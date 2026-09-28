@echo off
chcp 65001 >nul
REM ============================================================
REM  Atualiza os DOIS cenarios (estadual MA e nacional) com um clique.
REM  Antes: coloque as pesquisas novas em
REM    dados\pesquisas_verificadas.csv            (governador MA)
REM    nacional\dados\pesquisas_presidente.csv    (presidente)
REM ============================================================
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

echo.
echo [1/6] Cenario estadual: base municipal (TSE + prefeitos)...
python preparar_base.py || goto erro
echo [2/6] Cenario estadual: 6 agregadores de pesquisas...
python modelos_pesquisas.py >nul 2>&1 || goto erro
echo [3/6] Cenario estadual: municipios + Monte Carlo...
python modelo_municipios_mc.py > resultados\log_mc.txt 2>&1 || goto erro

cd nacional
echo [4/6] Cenario nacional: base por estado (TSE)...
python preparar_base_nacional.py >nul || goto erro_nac
echo [5/6] Cenario nacional: 6 agregadores de pesquisas...
python modelos_pesquisas_nacional.py >nul 2>&1 || goto erro_nac
echo [6/6] Cenario nacional: estados + Monte Carlo...
python modelo_ufs_mc.py > resultados\log_mc.txt 2>&1 || goto erro_nac
cd ..

echo.
python -c "import json; e=json.load(open('resultados/simulacao.json',encoding='utf-8'))['resultado_final']; n=json.load(open('nacional/resultados/simulacao_nacional.json',encoding='utf-8'))['resultado_final']; print(f'  Governo MA:  Braide {e[\"prob_braide_governador\"]:.0%%}  x  Orleans {e[\"prob_orleans_governador\"]:.0%%}'); print(f'  Presidente:  Lula {n[\"prob_lula_presidente\"]:.0%%}  x  Flavio {n[\"prob_flavio_presidente\"]:.0%%}')"
echo.
echo Pronto. Recarregue o painel no navegador (F5).
echo.
set /p ENVIAR=Enviar a atualizacao ao GitHub agora? (S/N):
if /i "%ENVIAR%"=="S" (
  git add -A
  git commit -m "Atualiza pesquisas e modelos"
  git push
)
pause
exit /b 0

:erro_nac
cd ..
:erro
echo.
echo *** ERRO na etapa acima. Veja a mensagem e o arquivo resultados\log_mc.txt ***
pause
exit /b 1
