import ast
from pathlib import Path
import unittest
from unittest.mock import Mock

class Stop(BaseException): pass

class BookingMailTests(unittest.TestCase):
    def data_flow(self, supabase_mode=True, fail=False):
        tree=ast.parse(Path('pages/1_Booking.py').read_text(encoding='utf-8'))
        # Execute the real page's data-mail branch, with all I/O mocked.
        candidates=[n for n in ast.walk(tree) if isinstance(n,ast.If) and isinstance(n.test,ast.Name) and n.test.id=='send_data']
        node=next(n for n in candidates if any(isinstance(x,ast.Call) and isinstance(x.func,ast.Name) and x.func.id=='add_data' for x in ast.walk(n)))
        env={n.id:Mock() for n in ast.walk(node) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load)}
        env.update(send_data=True, uses_supabase_auth=lambda:supabase_mode, is_restore_test=lambda:False, int=int, Exception=Exception)
        env['year']='2026'
        env['st'].stop.side_effect=Stop
        if fail: env['send_data_email'].side_effect=RuntimeError('SMTP failure')
        code=compile(ast.Module(body=[node],type_ignores=[]),'booking-mail','exec')
        return env,code
    def test_supabase_resending_data_mail_never_inserts(self):
        env,code=self.data_flow()
        exec(code,env); exec(code,env)
        self.assertEqual(env['send_data_email'].call_count,2)
        env['supabase'].table.assert_not_called()
    def test_mail_failure_does_not_insert(self):
        for mode in (True,False):
            env,code=self.data_flow(mode,True)
            with self.assertRaises(Stop): exec(code,env)
            env['supabase'].table.assert_not_called()
            env['st'].error.assert_called_once()
    def test_legacy_success_preserves_insert(self):
        env,code=self.data_flow(False)
        exec(code,env)
        env['supabase'].table.return_value.insert.assert_called_once()
