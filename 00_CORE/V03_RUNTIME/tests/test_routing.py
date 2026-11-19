import sys,unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from routing import Router
CATALOG=[{'model':name,'inputModalities':['text','image']} for name in ['gpt-6.1-sol','gpt-6-luna','gpt-6.1-terra','gpt-6-astra']]
class RouterTests(unittest.TestCase):
 def setUp(self):self.router=Router(CATALOG)
 def test_social_is_local_and_cheap(self):
  classify=Mock(side_effect=AssertionError('Não consultar IA em saudação'))
  r=self.router.select('alô vamos conversar',social=True,classify=classify)
  self.assertEqual(r.model,'gpt-6-luna');self.assertFalse(r.needs_memory);self.assertEqual(r.source,'local')
 def test_code_uses_coding_model(self):
  r=self.router.select('Corrigir bug em Python');self.assertEqual(r.model,'gpt-6.1-terra');self.assertEqual(r.task,'coding')
 def test_complex_analysis_uses_stronger_model(self):
  r=self.router.select('Compare arquitetura e segurança para esta aplicação');self.assertEqual(r.model,'gpt-6-astra')
 def test_images_require_vision(self):
  self.router.catalog['gpt-6-luna']['inputModalities']=['text']
  r=self.router.select('O que aparece?',images=1);self.assertEqual(r.model,'gpt-6.1-sol')
 def test_memory_preserved(self):
  r=self.router.select('O que você lembra das tarefas anteriores?');self.assertTrue(r.needs_memory);self.assertEqual(r.task,'memory')
 def test_ambiguous_calls_light_agent_and_caches_without_raw_reason(self):
  classify=Mock(return_value={'task':'chat','complexity':'low','reason':'texto privado não deve ser salvo'})
  r=self.router.select('Me ajude com esta ideia',classify=classify)
  self.assertEqual(r.source,'agente leve');self.assertNotIn('privado',r.reason)
  again=self.router.select('Me ajude com esta ideia',classify=classify)
  self.assertEqual(again.source,'cache em RAM');self.assertEqual(classify.call_count,1)
 def test_invalid_agent_reply_falls_back(self):
  r=self.router.select('Pedido ambíguo',classify=lambda text:{'task':'execute_shell','complexity':'low'})
  self.assertEqual(r.model,'gpt-6.1-sol');self.assertEqual(r.source,'fallback local')
 def test_missing_models_fall_back_to_available(self):
  router=Router([CATALOG[0]]);self.assertEqual(router.select('oi',social=True).model,'gpt-6.1-sol')
 def test_followup_preserves_model(self):
  self.router.previous=self.router.select('Depurar Python')
  self.assertEqual(self.router.select('explique melhor').model,'gpt-6.1-terra')
if __name__=='__main__':unittest.main(verbosity=2)
