"""Read-only LeetCode client. No credentials are accepted as tool arguments."""
import json
import os
import random
import re
import time
import urllib.error
import urllib.request

NC150 = set(map(str, [217,242,1,49,347,238,36,271,128,125,167,15,11,42,121,3,424,567,76,239,20,155,150,22,739,853,84,704,74,875,153,33,981,4,206,21,143,19,138,2,141,287,146,23,25,226,104,543,110,100,572,235,102,199,1448,98,230,105,124,297,208,211,212,703,1046,973,215,621,355,295,78,39,46,90,40,79,131,17,51,200,695,133,286,994,417,130,207,210,261,323,684,127,332,1584,743,778,269,787,70,746,198,213,5,647,91,322,152,139,300,416,62,1143,309,518,494,97,329,115,72,312,10,53,55,45,134,846,1899,763,678,57,56,435,252,253,1851,48,54,73,202,66,50,43,2013,191,338,190,268,371,7,136]))

class LeetCodeError(RuntimeError):
    pass

class Client:
    def __init__(self):
        self.session = os.getenv('LEETCODE_SESSION', '')
        self.csrf = os.getenv('LEETCODE_CSRF_TOKEN', '')
        self.expected_username = os.getenv('LEETCODE_USERNAME', '')
        self._catalog = None
        self._expires = 0
        self._username = None

    def _request(self, path, payload=None):
        headers = {'User-Agent': 'leetcode-study-mcp/0.1', 'Referer': 'https://leetcode.com/', 'Accept': 'application/json'}
        if self.session:
            # Never follow redirects carrying the session to another origin.
            headers['Cookie'] = 'LEETCODE_SESSION=' + self.session + ('; csrftoken=' + self.csrf if self.csrf else '')
        if self.csrf:
            headers['x-csrftoken'] = self.csrf
        body = None if payload is None else json.dumps(payload).encode()
        if body:
            headers['Content-Type'] = 'application/json'
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args):
                return None
        request = urllib.request.Request('https://leetcode.com' + path, data=body, headers=headers)
        try:
            with urllib.request.build_opener(NoRedirect()).open(request, timeout=30) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            raise LeetCodeError(f'LeetCode returned HTTP {exc.code}. Check session expiry or site access; no bypass attempted.') from None
        except (urllib.error.URLError, TimeoutError, ValueError):
            raise LeetCodeError('LeetCode request failed or returned non-JSON. Check connectivity and site access.') from None

    def graphql(self, query, variables=None):
        result = self._request('/graphql/', {'query': query, 'variables': variables or {}})
        if result.get('errors') or not isinstance(result.get('data'), dict):
            # Do not echo server error text that could contain request details.
            raise LeetCodeError('LeetCode GraphQL rejected the query. Its unofficial schema may have changed or authentication expired.')
        return result['data']

    def account(self):
        if not self.session:
            raise LeetCodeError('Set LEETCODE_SESSION locally to read full solved history and private submissions.')
        result = self.graphql('query { userStatus { isSignedIn username } }').get('userStatus') or {}
        if not result.get('isSignedIn') or not result.get('username'):
            raise LeetCodeError('Session is expired or invalid; full history cannot be inferred from public data.')
        if self.expected_username and result['username'].lower() != self.expected_username.lower():
            raise LeetCodeError('Signed-in account does not match LEETCODE_USERNAME.')
        self._username = result['username']
        return {'username': self._username, 'authenticated': True}

    def catalog(self, refresh=False):
        export = os.getenv('LEETCODE_CATALOG_FILE')
        if export:
            try:
                with open(export, encoding='utf-8') as file:
                    data = json.load(file)
            except (OSError, ValueError):
                raise LeetCodeError('Could not read LEETCODE_CATALOG_FILE JSON.') from None
            if not data.get('user_name'):
                raise LeetCodeError('Export has no signed-in username; export while logged in.')
            self._username = data['user_name']
            if self.expected_username and self._username.lower() != self.expected_username.lower():
                raise LeetCodeError('Export account does not match LEETCODE_USERNAME.')
            return self._parse_catalog(data)
        self.account()
        if not refresh and self._catalog is not None and time.monotonic() < self._expires:
            return self._catalog
        data = self._request('/api/problems/all/')
        questions = self._parse_catalog(data)
        self._catalog, self._expires = questions, time.monotonic() + 300
        return questions

    def _parse_catalog(self, data):
        if data.get('user_name') != self._username:
            raise LeetCodeError('Problem catalog is not authenticated for the expected account.')
        rows = data.get('stat_status_pairs')
        if not isinstance(rows, list) or not rows:
            raise LeetCodeError('LeetCode returned an empty or incompatible catalog.')
        questions = []
        for row in rows:
            stat = row['stat']
            questions.append({'id': str(stat['frontend_question_id']), 'title': stat['question__title'], 'slug': stat['question__title_slug'], 'difficulty': {1:'Easy',2:'Medium',3:'Hard'}[row['difficulty']['level']], 'paid': bool(row.get('paid_only')), 'status': row.get('status')})
        reported = data.get('num_solved')
        if reported is not None and sum(q['status'] == 'ac' for q in questions) != reported:
            raise LeetCodeError('Catalog solved count disagrees with account total; refusing incomplete recommendations.')
        return questions

    def solved(self, refresh=False):
        items = [q for q in self.catalog(refresh) if q['status'] == 'ac']
        return {'username': self._username, 'count': len(items), 'complete_catalog': True, 'problems': items}

    def recommend(self, count=10, difficulty='Medium', exclude_nc150=True, exclude_ids=None, seed=None, refresh=False):
        if not 1 <= count <= 50:
            raise ValueError('count must be between 1 and 50')
        if difficulty not in ('Easy','Medium','Hard','Any'):
            raise ValueError('difficulty must be Easy, Medium, Hard, or Any')
        excluded = set(map(str, exclude_ids or [])) | (NC150 if exclude_nc150 else set())
        pool = [q for q in self.catalog(refresh) if q['status'] != 'ac' and not q['paid'] and q['id'] not in excluded and (difficulty == 'Any' or q['difficulty'] == difficulty)]
        picks = random.Random(seed).sample(pool, min(count, len(pool)))
        # No tags, categories, status, or hints in recommendation output.
        return {'problems': [{'id': q['id'], 'title': q['title'], 'url': 'https://leetcode.com/problems/' + q['slug'] + '/'} for q in picks], 'eligible_count': len(pool)}

    def recent(self, username, limit=20):
        if not 1 <= limit <= 20:
            raise ValueError('limit must be between 1 and 20')
        data = self.graphql('query($username:String!,$limit:Int!){recentAcSubmissionList(username:$username,limit:$limit){id title titleSlug timestamp}}', {'username': username, 'limit': limit})
        return {'complete_history': False, 'submissions': data.get('recentAcSubmissionList') or []}

    def submissions(self, slug, offset=0, limit=20):
        self.account()
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', slug) or offset < 0 or not 1 <= limit <= 20:
            raise ValueError('Use a valid problem slug, nonnegative offset, and limit 1..20')
        return self.graphql('query($questionSlug:String!,$offset:Int!,$limit:Int!){questionSubmissionList(questionSlug:$questionSlug,offset:$offset,limit:$limit){hasNext lastKey submissions{id statusDisplay lang timestamp}}}', {'questionSlug':slug,'offset':offset,'limit':limit})

    def submission(self, submission_id):
        self.account()
        if not submission_id.isdigit():
            raise ValueError('submission_id must contain only digits')
        return self.graphql('query($submissionId:Int!){submissionDetails(submissionId:$submissionId){id code lang{name} runtime memory}}', {'submissionId':int(submission_id)})
