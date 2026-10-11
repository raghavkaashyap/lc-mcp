import unittest
import json
import tempfile
from unittest.mock import patch
from core import Client, LeetCodeError, NC150

class Tests(unittest.TestCase):
    def client(self):
        c = Client()
        c.catalog = lambda refresh=False: [
            {'id':str(i),'title':f'Problem {i}','slug':f'problem-{i}','status':status,'paid':paid,'difficulty':difficulty}
            for i,status,paid,difficulty in [(1,None,False,'Medium'),(560,'ac',False,'Medium'),(9001,None,False,'Medium'),(9002,None,True,'Medium'),(9003,None,False,'Hard'),(9004,None,False,'Medium')]]
        return c

    def test_exclusion_and_hint_free(self):
        output = self.client().recommend(10, exclude_ids=['9004'], seed=1)
        self.assertEqual([p['id'] for p in output['problems']], ['9001'])
        self.assertEqual(set(output['problems'][0]), {'id','title','url'})

    def test_nc150(self):
        self.assertEqual(len(NC150), 150)
        self.assertIn('763', NC150)

    def test_missing_and_invalid_auth(self):
        c = Client(); c.session = ''
        with self.assertRaises(LeetCodeError): c.account()
        c.session = 'fake'; c.graphql = lambda *args: {'userStatus': {'isSignedIn':False}}
        with self.assertRaises(LeetCodeError): c.account()

    def test_account_mismatch(self):
        c = Client(); c.session = 'fake'; c.expected_username = 'me'
        c.graphql = lambda *args: {'userStatus': {'isSignedIn':True,'username':'other'}}
        with self.assertRaises(LeetCodeError): c.account()

    def test_incomplete_catalog(self):
        c = Client(); c.account = lambda: None; c._username = 'me'
        c._request = lambda *args: {'user_name':'me','num_solved':1,'stat_status_pairs':[{'stat':{'frontend_question_id':1,'question__title':'Two Sum','question__title_slug':'two-sum'},'difficulty':{'level':1},'status':None}]}
        with self.assertRaises(LeetCodeError): c.catalog()

    def test_validation(self):
        for kwargs in ({'count':0},{'count':51},{'difficulty':'Oops'}):
            with self.assertRaises(ValueError): self.client().recommend(**kwargs)

    def test_public_history_is_partial(self):
        c = Client(); c.graphql = lambda *args: {'recentAcSubmissionList':[]}
        self.assertFalse(c.recent('me')['complete_history'])

    def test_graphql_error_is_sanitized(self):
        c = Client(); c._request = lambda *args: {'errors':[{'message':'SECRET'}]}
        with self.assertRaises(LeetCodeError) as error: c.graphql('query {}')
        self.assertNotIn('SECRET', str(error.exception))

    def test_offline_export_without_session(self):
        data = {'user_name':'me','num_solved':0,'stat_status_pairs':[{'stat':{'frontend_question_id':560,'question__title':'Subarray Sum Equals K','question__title_slug':'subarray-sum-equals-k'},'difficulty':{'level':2},'status':None}]}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as file:
            json.dump(data, file); file.flush()
            with patch.dict('os.environ', {'LEETCODE_CATALOG_FILE':file.name,'LEETCODE_USERNAME':'me','LEETCODE_SESSION':''}):
                c = Client()
                self.assertEqual(c.recommend()['problems'][0]['id'], '560')

if __name__ == '__main__': unittest.main()
