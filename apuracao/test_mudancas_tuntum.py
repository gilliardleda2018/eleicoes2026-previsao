import unittest
from streamlit.testing.v1 import AppTest
from apuracao.mudancas_tuntum import analisar


class TuntumTest(unittest.TestCase):
    def test_primeira_e_zero(self):
        linhas=analisar(None,dict(votos={'A':0,'B':0},percentual=0))
        self.assertIn('ainda não tem votos',linhas[0])
        self.assertFalse(any('à frente' in x for x in linhas))

    def test_virada_revisao_e_margem(self):
        a=dict(votos={'A':100,'B':80,'C':20},percentual=20)
        b=dict(votos={'A':90,'B':120,'C':25},percentual=19)
        linhas=analisar(a,b)
        texto=' '.join(linhas)
        self.assertIn('A → B',texto)
        self.assertIn('−',texto.replace('-', '−'))
        self.assertIn('revisão da fonte',texto)
        self.assertIn('+20 para -30',texto)
        self.assertIn('Percentual revisado',texto)

    def test_cache_sem_mudanca(self):
        a=dict(votos={'A':100,'B':80},percentual=20)
        self.assertIn('Nenhuma mudança local', ' '.join(analisar(a,a)))

    def test_interface_tres_esferas(self):
        for disputa in ['presidente','governador','deputado']:
            code=f'''from apuracao.mudancas_tuntum import mostrar
mostrar({disputa!r},1,True,{{"<A>":100,"B":80}},20,1)
mostrar({disputa!r},1,True,{{"<A>":90,"B":120}},40,2)
'''
            app=AppTest.from_string(code).run()
            self.assertFalse(app.exception)
            texto=' '.join(x.value for x in app.markdown)
            self.assertIn('O que mudou em Tuntum?',texto)
            self.assertIn('ENSAIO',texto)
            self.assertIn('&lt;A&gt;',texto)
            self.assertIn('Mudança de liderança',texto)

    def test_indisponivel_nao_zero(self):
        code='''from apuracao.mudancas_tuntum import mostrar
mostrar('presidente',1,True,None,None,1)'''
        app=AppTest.from_string(code).run()
        self.assertFalse(app.exception)
        texto=' '.join(x.value for x in app.markdown)
        self.assertIn('sem recorte municipal',texto)
        self.assertNotIn('0 votos',texto)
