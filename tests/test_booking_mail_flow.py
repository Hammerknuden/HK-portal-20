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
        env.update(str=str, send_data=True, uses_supabase_auth=lambda:supabase_mode, is_restore_test=lambda:False, int=int, Exception=Exception)
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

    def test_empty_number_blocks_confirmation_in_all_languages(self):
        tree=ast.parse(Path('pages/1_Booking.py').read_text(encoding='utf-8'))
        parent=next(n for n in ast.walk(tree) if isinstance(n,ast.Assign)
                    and any(isinstance(t,ast.Name) and t.id=='booking_submitted' for t in n.targets))
        body=next(value for n in ast.walk(tree) for _,value in ast.iter_fields(n) if isinstance(value,list) and parent in value)
        start=body.index(parent)+1
        end=next(i for i in range(start,len(body)) if isinstance(body[i],ast.Assign)
                 and any(isinstance(t,ast.Name) and t.id=='send_data' for t in body[i].targets))
        nodes=body[start:end]
        for number in ('', '   ', None):
            for language in ('DK','UK','DE'):
                env={n.id:Mock() for node in nodes for n in ast.walk(node) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load)}
                env.update(str=str, Exception=Exception, booking_submitted=True, booking_number=number, Sprog=language)
                env['st'].stop.side_effect=Stop
                with self.assertRaises(Stop):
                    exec(compile(ast.Module(body=nodes,type_ignores=[]),'confirmation','exec'),env)
                for name in ('send_danish_confirmation_email','send_english_confirmation_email','send_german_confirmation_email'):
                    env[name].assert_not_called()
                env['st'].warning.assert_called_once()
    def test_empty_number_blocks_data_mail_and_export(self):
        for number in ('', '   ', None):
            env,code=self.data_flow()
            env['booking_number']=number
            with self.assertRaises(Stop): exec(code,env)
            env['add_data'].assert_not_called()
            env['send_data_email'].assert_not_called()
            env['supabase'].table.assert_not_called()
