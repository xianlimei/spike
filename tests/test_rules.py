from time import strftime, localtime
import re

from sqlalchemy.orm.exc import UnmappedInstanceError

try:
    from urlparse import urlparse
except ImportError:  # python3
    from urllib.parse import urlparse

from spike import create_app
from spike.model import db
from spike.model.naxsi_rules import NaxsiRules
import unittest


class FlaskrTestCase(unittest.TestCase):
    def setUp(self):
        app = create_app()
        db.init_app(app)
        app.config['TESTING'] = True
        self.app = app.test_client()

    def tearDown(self):
        pass

    def __create_rule(self):
        """

        :return int: The id of the new rule
        """
        current_sid = NaxsiRules.query.order_by(NaxsiRules.sid.desc()).first()
        current_sid = 1337 if current_sid is None else current_sid.sid + 1

        db.session.add(NaxsiRules(u'POUET', 'str:test', u'BODY', u'$SQL:8', current_sid, u'web_server.rules',
                                  u'f hqewifueiwf hueiwhf uiewh fiewh fhw', '1', True, 1457101045))
        self.sid_to_delete = current_sid
        return current_sid

    def __delete_rule(self, sid=None):
        sid = self.sid_to_delete if sid is None else sid
        try:
            db.session.delete(NaxsiRules.query.filter(sid == NaxsiRules.sid).first())
        except UnmappedInstanceError:  # who cares ?
            pass

    def test_index(self):
        rv = self.app.get('/', follow_redirects=True)
        self.assertEqual(rv.status_code, 200)
        self.assertIn('<title>SPIKE! - WAF Rules Builder</title>', rv.data)
        self.assertTrue(re.search(r'<h2>Naxsi - Rules \( \d+ \)</h2>', rv.data) is not None)

    def test_add_rule(self):
        data = {
            'msg': 'this is a test message',
            'detection': 'DETECTION',
            'mz': 'BODY',
            'custom_mz_val': '',
            'negative': 'checked',
            'score_$SQL': 8,
            'score': '$SQL',
            'rmks': 'this is a test remark',
            'ruleset': 'scanner.rules'
        }
        rv = self.app.post('/rules/new', data=data, follow_redirects=True)
        _rule = NaxsiRules.query.order_by(NaxsiRules.sid.desc()).first()

        self.assertIn(('<li> - OK: created %d : %s</li>' % (_rule.sid, _rule.msg)), rv.data)
        self.assertEqual(_rule.msg, data['msg'])
        self.assertEqual(_rule.detection, 'str:' + data['detection'])
        self.assertEqual(_rule.mz, data['mz'])
        self.assertEqual(_rule.score, data['score'] + ':' + str(data['score_$SQL']))
        self.assertEqual(_rule.rmks, data['rmks'])
        self.assertEqual(_rule.ruleset, data['ruleset'])

        self.__delete_rule(_rule.sid)

    def test_del_rule(self):
        old_sid = self.__create_rule()

        db.session.add(NaxsiRules(u'POUET', 'str:test', u'BODY', u'$SQL:8', old_sid + 1, u'web_server.rules',
                                  u'f hqewifueiwf hueiwhf uiewh fiewh fhw', '1', True, 1457101045))
        rv = self.app.get('/rules/del/%d' % (old_sid + 1))
        self.assertEqual(rv.status_code, 302)

        _rule = NaxsiRules.query.order_by(NaxsiRules.sid.desc()).first()
        self.assertEqual(_rule.sid, old_sid)

        self.__delete_rule()

    def test_plain_rule(self):
        self.__create_rule()
        _rule = NaxsiRules.query.order_by(NaxsiRules.sid.desc()).first()
        rv = self.app.get('/rules/plain/%d' % _rule.sid)
        self.assertEqual(rv.status_code, 200)
        rdate = strftime("%F - %H:%M", localtime(float(str(_rule.timestamp))))
        rmks = "# ".join(_rule.rmks.strip().split("\n"))
        detect = _rule.detection.lower() if _rule.detection.startswith("str:") else _rule.detection
        negate = 'negative' if _rule.negative == 1 else ''
        expected = """
#
# sid: %s | date: %s
#
# %s
#
MainRule %s "%s" "msg:%s" "mz:%s" "s:%s" id:%s ;

""" % (_rule.sid, rdate, rmks, negate, detect, _rule.msg, _rule.mz, _rule.score, _rule.sid)
        self.assertEqual(expected, rv.data)
        self.__delete_rule()
