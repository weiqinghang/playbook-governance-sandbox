#!/usr/bin/env python3
"""GitHub.com personal-repository governance. Labels are authoritative.

All writes require --apply. Project columns are disposable projections, never
commands: dragging a card does not authorize a workflow or closeout transition.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import quote

WORKFLOW = ('backlog', 'ready', 'doing', 'verify', 'writeback', 'done')
MATURITY = ('idea', 'shaping', 'ready-for-dev', 'parked')
FIELDS = {'Workflow': WORKFLOW, 'Backlog maturity': MATURITY}
COLORS = ('GRAY', 'BLUE', 'YELLOW', 'PURPLE', 'GREEN', 'PINK')


class PolicyError(ValueError): pass


class GitHub:
    def __init__(self, repo):
        if not re.fullmatch(r'[\w.-]+/[\w.-]+', repo):
            raise PolicyError('expected owner/repository')
        self.repo = repo
        self.owner = repo.split('/')[0]
        self.base = 'repos/' + repo

    def api(self, endpoint, method='GET', body=None):
        cmd = ['gh', 'api', '--hostname', 'github.com', endpoint, '-X', method]
        if body is not None: cmd += ['--input', '-']
        out = subprocess.run(cmd, input=json.dumps(body) if body is not None else None,
                             text=True, capture_output=True)
        if out.returncode:
            # Do not reflect arbitrary API bodies or credentials to logs.
            raise PolicyError(f'GitHub {method} {endpoint.split("?")[0]} failed')
        return json.loads(out.stdout) if out.stdout.strip() else None

    def graphql(self, query, **variables):
        result = self.api('graphql', 'POST', {'query': query, 'variables': variables})
        if result.get('errors'): raise PolicyError('GraphQL operation failed')
        return result['data']

    def pages(self, endpoint):
        rows = []
        for page in range(1, 1001):
            sep = '&' if '?' in endpoint else '?'
            batch = self.api(f'{endpoint}{sep}per_page=100&page={page}')
            if not isinstance(batch, list): raise PolicyError('invalid paged response')
            rows.extend(batch)
            if len(batch) < 100: return rows
        raise PolicyError('pagination limit')

    def identity(self):
        repo = self.api(self.base)
        if repo.get('full_name', '').lower() != self.repo.lower(): raise PolicyError('repository mismatch')
        if repo['owner']['type'] != 'User': raise PolicyError('v1 supports personal repositories only')
        return repo


def label_names(issue):
    return [v['name'] if isinstance(v, dict) else v for v in issue.get('labels', [])]


def projection(issue):
    labels = label_names(issue)
    result = {}
    for field, prefix, allowed in [('Workflow', 'workflow::', WORKFLOW), ('Backlog maturity', 'backlog::', MATURITY)]:
        values = [v[len(prefix):] for v in labels if v.startswith(prefix)]
        if len(values) != 1 or values[0] not in allowed:
            raise PolicyError(f'{prefix} must have exactly one known label')
        result[field] = values[0]
    if result['Workflow'] != 'backlog' and result['Backlog maturity'] != 'ready-for-dev':
        raise PolicyError('delivery requires ready-for-dev')
    return result


def desired_labels():
    return ([{'name': 'workflow::'+v, 'color': '428BCA'} for v in WORKFLOW]
            + [{'name': 'backlog::'+v, 'color': '5CB85C'} for v in MATURITY]
            + [{'name': v, 'color': '8E7CC3'} for v in
               ['type::bug', 'type::chore', 'sizing::micro', 'sizing::standard', 'sizing::heavy',
                'delivery::architecting', 'delivery::implementing', 'delivery::unblocking']])


def ensure_labels(client, apply):
    existing = {v['name'] for v in client.pages(client.base + '/labels')}
    missing = [v for v in desired_labels() if v['name'] not in existing]
    if apply:
        for label in missing: client.api(client.base + '/labels', 'POST', label)
        found = {v['name'] for v in client.pages(client.base + '/labels')}
        if not {v['name'] for v in desired_labels()} <= found: raise PolicyError('label readback failed')
    return [v['name'] for v in missing]


def projects(client):
    rows, cursor = [], None
    while True:
        data = client.graphql('''query($owner:String!,$cursor:String){user(login:$owner){
          id projectsV2(first:100,after:$cursor){nodes{id number title shortDescription url}
          pageInfo{hasNextPage endCursor}}}}''', owner=client.owner, cursor=cursor)['user']
        page = data['projectsV2']; rows.extend(page['nodes'])
        if not page['pageInfo']['hasNextPage']: return data['id'], rows
        cursor = page['pageInfo']['endCursor']


def fields(client, project):
    data = client.graphql('''query($id:ID!){node(id:$id){... on ProjectV2{
      fields(first:100){nodes{... on ProjectV2Field{id name databaseId}
      ... on ProjectV2SingleSelectField{id name databaseId options{id name}}}
      pageInfo{hasNextPage}}}}}''', id=project['id'])['node']['fields']
    if data['pageInfo']['hasNextPage']: raise PolicyError('field limit exceeded')
    return data['nodes']


def views(client, project):
    data = client.graphql('''query($id:ID!){node(id:$id){... on ProjectV2{
      views(first:100){nodes{id name layout filter verticalGroupByFields(first:10){nodes{
      ... on ProjectV2Field{id name} ... on ProjectV2SingleSelectField{id name}}}}
      pageInfo{hasNextPage}}}}}''', id=project['id'])['node']['views']
    if data['pageInfo']['hasNextPage']: raise PolicyError('view limit exceeded')
    return data['nodes']


def validate_recovery(client, project):
    """Only an explicitly selected, empty default project may be recovered."""
    data = client.graphql("""query($id:ID!){node(id:$id){... on ProjectV2{
      items(first:1){totalCount} repositories(first:1){totalCount}}}}""", id=project['id'])['node']
    if data['items']['totalCount'] or data['repositories']['totalCount']:
        raise PolicyError('recovery requires an empty unlinked project')
    defaults = {'Title','Assignees','Status','Labels','Linked pull requests','Milestone','Repository','Reviewers',
                'Parent issue','Sub-issues progress','Issue type','Blocked by','Blocking','Tracked by','Tracks'}
    fs = fields(client, project)
    if any(f.get('name') not in defaults for f in fs):
        raise PolicyError('custom project fields prevent recovery')
    status = [f for f in fs if f.get('name') == 'Status']
    if len(status) != 1 or [o['name'] for o in status[0].get('options', [])] != ['Todo','In Progress','Done']:
        raise PolicyError('custom project status prevents recovery')
    vs = views(client, project)
    if len(vs) != 1 or vs[0]['name'] != 'View 1' or vs[0]['layout'] != 'TABLE_LAYOUT' or vs[0].get('filter'):
        raise PolicyError('custom project views prevent recovery')


def ensure_project(client, apply, recover_project=None):
    title = client.repo.split('/')[1] + ' · Governance'
    marker = 'Playbook label projection for ' + client.repo
    owner_id, existing = projects(client)
    matches = [p for p in existing if p['title'] == title]
    if len(matches) > 1: raise PolicyError('ambiguous governance project')
    if matches and matches[0].get('shortDescription') != marker:
        candidate = matches[0]
        if recover_project != candidate['number'] or candidate.get('shortDescription'):
            raise PolicyError('same-name project is not managed; explicit empty-project recovery required')
        validate_recovery(client, candidate)
        if not apply:
            return {'planned_recovery': candidate['number']}
        client.graphql("""mutation($id:ID!,$description:String!){updateProjectV2(input:{projectId:$id,shortDescription:$description}){
          projectV2{id}}}""", id=candidate['id'], description=marker)
        _, reread = projects(client)
        candidate = next(p for p in reread if p['id'] == candidate['id'])
        if candidate.get('shortDescription') != marker:
            raise PolicyError('project recovery readback failed')
        matches = [candidate]
    if not matches:
        if not apply: return {'planned_title': title}
        p = client.graphql('''mutation($owner:ID!,$title:String!){createProjectV2(input:{ownerId:$owner,title:$title}){
          projectV2{id number title url}}}''', owner=owner_id, title=title)['createProjectV2']['projectV2']
        client.graphql('''mutation($id:ID!,$description:String!){updateProjectV2(input:{projectId:$id,shortDescription:$description}){
          projectV2{id}}}''', id=p['id'], description=marker)
        matches = [p]
    project = matches[0]
    current = fields(client, project)
    for name, options in FIELDS.items():
        found = [f for f in current if f['name'] == name]
        if len(found) > 1: raise PolicyError('ambiguous projection field')
        if found and [v['name'] for v in found[0].get('options', [])] != list(options):
            raise PolicyError('customized projection field preserved; resolve conflict')
        if not found and apply:
            client.graphql('''mutation($id:ID!,$name:String!,$options:[ProjectV2SingleSelectFieldOptionInput!]!){
              createProjectV2Field(input:{projectId:$id,name:$name,dataType:SINGLE_SELECT,singleSelectOptions:$options}){
              projectV2Field{... on ProjectV2SingleSelectField{id}}}}''', id=project['id'], name=name,
              options=[{'name': v, 'description': 'Projection of Issue labels', 'color': COLORS[i % len(COLORS)]}
                       for i, v in enumerate(options)])
    if not apply: return project
    current = {f['name']: f for f in fields(client, project)}
    existing_views = views(client, project)
    user_id = client.owner  # The live personal Projects endpoint resolves login, not numeric REST id.
    for name, field, filter_ in [('Discovery', 'Backlog maturity', 'is:issue label:"workflow::backlog"'),
                                  ('Delivery', 'Workflow', 'is:issue -label:"workflow::backlog"')]:
        matches = [v for v in existing_views if v['name'] == name]
        if len(matches) > 1: raise PolicyError('ambiguous board view')
        if not matches:
            client.api(f'users/{user_id}/projectsV2/{project["number"]}/views', 'POST',
                       {'name': name, 'layout': 'board', 'filter': filter_,
                        'vertical_group_by': [current[field]['databaseId']]})
    repository = client.identity()
    client.graphql("""mutation($project:ID!,$repo:ID!){linkProjectV2ToRepository(input:{projectId:$project,repositoryId:$repo}){
      repository{id}}}""", project=project['id'], repo=repository['node_id'])
    actual = views(client, project)
    for name, field in [('Discovery', 'Backlog maturity'), ('Delivery', 'Workflow')]:
        matched = [v for v in actual if v['name'] == name]
        if len(matched) != 1 or matched[0]['layout'] != 'BOARD_LAYOUT':
            raise PolicyError('board layout readback failed')
        expected_filter = 'is:issue label:"workflow::backlog"' if name == 'Discovery' else 'is:issue -label:"workflow::backlog"'
        if matched[0].get('filter') != expected_filter:
            raise PolicyError('customized board filter preserved; resolve conflict')
        if [f['name'] for f in matched[0]['verticalGroupByFields']['nodes']] != [field]:
            raise PolicyError('board column readback failed')
    return project


def project_by_number(client, number):
    _, rows = projects(client)
    matches = [p for p in rows if p['number'] == number]
    if len(matches) != 1 or matches[0].get('shortDescription') != 'Playbook label projection for ' + client.repo:
        raise PolicyError('project does not belong to repository governance')
    return matches[0]


def sync_issue(client, number, project, apply):
    issue = client.api(client.base + f'/issues/{number}')
    if 'pull_request' in issue: raise PolicyError('Issue required, not PR')
    values = projection(issue)  # Validate all authority before any write.
    if not apply: return {'issue': number, 'projection': values}
    item = client.graphql('''mutation($project:ID!,$content:ID!){addProjectV2ItemById(input:{projectId:$project,contentId:$content}){
      item{id}}}''', project=project['id'], content=issue['node_id'])['addProjectV2ItemById']['item']['id']
    fs = {f['name']: f for f in fields(client, project)}
    for name, value in values.items():
        field = fs[name]
        option = next((o['id'] for o in field['options'] if o['name'] == value), None)
        if option is None: raise PolicyError('projection option missing')
        client.graphql('''mutation($project:ID!,$item:ID!,$field:ID!,$option:String!){
          updateProjectV2ItemFieldValue(input:{projectId:$project,itemId:$item,fieldId:$field,value:{singleSelectOptionId:$option}}){
          projectV2Item{id}}}''', project=project['id'], item=item, field=field['id'], option=option)
    result = client.graphql('''query($id:ID!){node(id:$id){... on ProjectV2Item{fieldValues(first:100){nodes{
      ... on ProjectV2ItemFieldSingleSelectValue{name field{... on ProjectV2SingleSelectField{name}}}}}}}}''', id=item)
    actual = {v['field']['name']: v['name'] for v in result['node']['fieldValues']['nodes'] if 'field' in v}
    if any(actual.get(k) != v for k, v in values.items()): raise PolicyError('projection readback failed')
    if projection(client.api(client.base + f'/issues/{number}')) != values:
        raise PolicyError('Issue changed during projection; rerun sync')
    return {'issue': number, 'item': item, 'projection': values, 'verified': True}


def transition(client, number, workflow, maturity, apply):
    endpoint = client.base + f'/issues/{number}'
    issue = client.api(endpoint)
    if 'pull_request' in issue or issue.get('state') != 'open': raise PolicyError('open Issue required')
    projection(issue)
    labels = [v for v in label_names(issue) if not v.startswith(('workflow::', 'backlog::'))]
    labels += ['workflow::' + workflow, 'backlog::' + maturity]
    proposal = {**issue, 'labels': labels}
    projection(proposal)
    if workflow in ('ready', 'doing', 'verify', 'writeback'):
        from git_workflow_guard import execution_decision
        decision = execution_decision(current_branch='work', default_branch='main', protected_branches=[],
                                      issue=proposal)
        if decision['decision'] != 'allow': raise PolicyError(decision['reason'])
    if apply:
        # Replace only the two managed scopes; preserve all other labels from fresh readback.
        client.api(endpoint, 'PATCH', {'labels': labels})
        read = client.api(endpoint)
        if set(label_names(read)) != set(labels) or read['state'] != issue['state']:
            raise PolicyError('transition readback failed')
    return {'issue': number, 'labels': labels, 'applied': apply}


def milestone(client, title, apply):
    matches = [m for m in client.pages(client.base + '/milestones?state=all') if m['title'] == title]
    if len(matches) > 1: raise PolicyError('ambiguous milestone')
    if matches: return matches[0]
    if not apply: return {'planned_title': title}
    created = client.api(client.base + '/milestones', 'POST', {'title': title})
    read = client.api(client.base + '/milestones/' + str(created['number']))
    if read['title'] != title: raise PolicyError('milestone readback failed')
    return read


def merge_preflight(client, number, issue_number):
    pr = client.api(client.base + f'/pulls/{number}')
    repo = client.identity()
    if pr['state'] != 'open' or pr.get('draft') or pr.get('mergeable') is not True:
        raise PolicyError('PR is not ready for merge')
    if pr['base']['ref'] != repo['default_branch'] or pr['head']['ref'] == pr['base']['ref']:
        raise PolicyError('invalid PR branches')
    owner, name = client.repo.split('/', 1)
    closing = client.graphql("""query($owner:String!,$name:String!,$number:Int!){repository(owner:$owner,name:$name){
      pullRequest(number:$number){closingIssuesReferences(first:1){totalCount}}}}""",
      owner=owner, name=name, number=number)['repository']['pullRequest']['closingIssuesReferences']['totalCount']
    if closing:
        raise PolicyError('PR would close Issues; separate closeout required')
    body = pr.get('body') or ''
    if not re.search(rf'(?<!\w)#{issue_number}(?!\d)', body): raise PolicyError('governing Issue missing')
    if re.search(r'\b(close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s+(?:[\w.-]+/[\w.-]+)?#\d+', body, re.I):
        raise PolicyError('automatic close keywords require separate closeout; use refs')
    issue = client.api(client.base + f'/issues/{issue_number}')
    if issue.get('pull_request'): raise PolicyError('governing Issue must not be a PR')
    projection(issue)
    from git_workflow_guard import execution_decision
    decision = execution_decision(current_branch='work', default_branch='main', protected_branches=[], issue=issue)
    if decision['decision'] != 'allow': raise PolicyError(decision['reason'])
    sha = pr['head']['sha']
    notes = client.pages(client.base + f'/issues/{number}/comments')
    reviews = [n for n in notes if n.get('user', {}).get('login') and
               re.search(r'(?m)^Agent:\s*reviewer\s*$', n.get('body', '')) and
               re.search(r'(?m)^Instance:\s*reviewer:\S+\s*$', n['body']) and
               re.search(r'(?m)^Via:\s*Codex\s*$', n['body']) and
               re.search(r'(?m)^head_sha:\s*' + re.escape(sha) + r'\s*$', n['body'])]
    if not reviews or not re.search(r'(?m)^review_result:\s*review pass\s*$', reviews[-1]['body']):
        raise PolicyError('latest independent review must pass exact PR HEAD')
    # Platform evaluates required checks/reviews/rules; unknown, behind, blocked all fail closed.
    if pr.get('mergeable_state') not in ('clean',): raise PolicyError('platform merge gates not clean')
    fresh = client.api(client.base + f'/pulls/{number}')
    if fresh['head']['sha'] != sha: raise PolicyError('PR changed during preflight')
    return {'decision': 'allow', 'head_sha': sha, 'pr': number, 'governing_issue': issue_number,
            'merge_authorized': False}


def protect_default(client, check, apply):
    """Explicit setup, separate from label/view initialization; never overwrite custom policy."""
    if not check or len(check) > 100:
        raise PolicyError('required check context must be nonempty and bounded')
    desired = {'name': 'Playbook governance', 'target': 'branch', 'enforcement': 'active',
      'bypass_actors': [],
      'conditions': {'ref_name': {'include': ['~DEFAULT_BRANCH'], 'exclude': []}},
      'rules': [{'type': 'deletion'}, {'type': 'non_fast_forward'},
        {'type': 'pull_request', 'parameters': {'required_approving_review_count': 0,
          'dismiss_stale_reviews_on_push': True, 'require_code_owner_review': False,
          'require_last_push_approval': False, 'required_review_thread_resolution': True}},
        {'type': 'required_status_checks', 'parameters': {'strict_required_status_checks_policy': True,
          'required_status_checks': [{'context': check}]}}]}
    matches = [r for r in client.pages(client.base + '/rulesets') if r['name'] == desired['name']]
    if len(matches) > 1:
        raise PolicyError('ambiguous ruleset')
    if matches:
        read = client.api(client.base + '/rulesets/' + str(matches[0]['id']))
        read.setdefault('bypass_actors', [])
        # Native response may add fields. Compare only requested policy, recursively.
        def contains(actual, expected):
            if isinstance(expected, dict):
                return isinstance(actual, dict) and all(k in actual and contains(actual[k], v) for k,v in expected.items())
            if isinstance(expected, list):
                return isinstance(actual, list) and len(actual) == len(expected) and all(contains(a,b) for a,b in zip(actual,expected))
            return actual == expected
        if not contains(read, desired):
            raise PolicyError('existing ruleset differs; preserve and review separately')
        return {'id': read['id'], 'verified': True}
    if not apply:
        return {'planned_ruleset': desired}
    made = client.api(client.base + '/rulesets', 'POST', desired)
    result = protect_default(client, check, False)
    if result.get('id') != made['id']:
        raise PolicyError('ruleset readback failed')
    return result


def verify_assets(directory, manifest_path):
    root = Path(directory).resolve()
    manifest = json.loads(Path(manifest_path).read_text())
    if manifest.get('schema_version') != 1 or not isinstance(manifest.get('files'), list) or not manifest['files']:
        raise PolicyError('invalid asset manifest')
    seen = set()
    for entry in manifest['files']:
        name = entry['name']
        if not isinstance(name, str) or Path(name).name != name or name in seen or name in ('.', '..'):
            raise PolicyError('unsafe or duplicate asset name')
        seen.add(name)
        path = root / name
        if path.is_symlink() or path.resolve().parent != root or not path.is_file(): raise PolicyError('unsafe asset')
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']: raise PolicyError('asset hash mismatch')
    return {'verified': sorted(seen)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True)
    parser.add_argument('--apply', action='store_true')
    sub = parser.add_subparsers(dest='command', required=True)
    init = sub.add_parser('init'); init.add_argument('--recover-project', type=int)
    sync = sub.add_parser('sync'); sync.add_argument('--issue', type=int, required=True); sync.add_argument('--project', type=int, required=True)
    move = sub.add_parser('transition'); move.add_argument('--issue', type=int, required=True)
    move.add_argument('--workflow', choices=WORKFLOW, required=True); move.add_argument('--maturity', choices=MATURITY, required=True)
    mile = sub.add_parser('milestone'); mile.add_argument('--title', required=True)
    merge = sub.add_parser('merge-preflight'); merge.add_argument('--pr', type=int, required=True); merge.add_argument('--issue', type=int, required=True)
    protect = sub.add_parser('protect-default'); protect.add_argument('--check', required=True)
    assets = sub.add_parser('verify-assets'); assets.add_argument('--directory', type=Path, required=True); assets.add_argument('--manifest', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == 'verify-assets':
            print(json.dumps(verify_assets(args.directory, args.manifest))); return 0
        client = GitHub(args.repo); client.identity()
        if args.command == 'init':
            result = {'labels_created_or_planned': ensure_labels(client, args.apply), 'project': ensure_project(client, args.apply, args.recover_project)}
        elif args.command == 'sync': result = sync_issue(client, args.issue, project_by_number(client, args.project), args.apply)
        elif args.command == 'transition': result = transition(client, args.issue, args.workflow, args.maturity, args.apply)
        elif args.command == 'milestone': result = milestone(client, args.title, args.apply)
        elif args.command == 'protect-default': result = protect_default(client, args.check, args.apply)
        else: result = merge_preflight(client, args.pr, args.issue)
        print(json.dumps(result, ensure_ascii=False, indent=2)); return 0
    except (PolicyError, KeyError, TypeError, OSError, StopIteration) as error:
        print(json.dumps({'decision': 'deny', 'reason': str(error)}, ensure_ascii=False)); return 2

if __name__ == '__main__': raise SystemExit(main())
