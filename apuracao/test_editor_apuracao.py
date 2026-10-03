import unittest
from apuracao.editor_apuracao import analisar


class EditorTest(unittest.TestCase):
    def test_inicio_e_sem_mudanca(self):
        x={'votos':{'A':0,'B':0},'percentual':0,'unidades':{}}
        self.assertIn('iniciado',analisar(None,x)[0][0])
        self.assertIn('Nenhuma mudança',analisar(x,x)[0][0])

    def test_virada_revisao_e_prioridade(self):
        a={'votos':{'A':100,'B':90},'percentual':50,'unidades':{
            'Tuntum':{'votos':{'A':10,'B':9},'percentual':50},
            'Outra cidade':{'votos':{'A':100,'B':0},'percentual':50}}}
        b={'votos':{'A':95,'B':110},'percentual':49,'unidades':{
            'Tuntum':{'votos':{'A':10,'B':11},'percentual':60},
            'Outra cidade':{'votos':{'A':10000,'B':0},'percentual':90}}}
        resumo,destaques=analisar(a,b)
        self.assertTrue(any('liderança' in x for x in resumo))
        self.assertTrue(any('revisão' in x for x in resumo))
        self.assertEqual(destaques[0]['nome'],'Tuntum')
        self.assertNotIn('eleito',' '.join(resumo))

    def test_interface_e_html(self):
        from streamlit.testing.v1 import AppTest
        a=AppTest.from_string('''from apuracao import editor_apuracao
x={'votos':{'<script>':10,'B':9},'percentual':1,'unidades':{}}
y={'votos':{'<script>':12,'B':11},'percentual':2,'unidades':{}}
editor_apuracao.mostrar([x,y],True)
''').run()
        self.assertFalse(a.exception)
        texto=' '.join(x.value for x in a.markdown)
        self.assertIn('O que mudou agora?',texto)
        self.assertIn('&lt;script&gt;',texto)
        self.assertIn('ENSAIO',texto)


if __name__=='__main__':unittest.main()
