# Coletor Moodle-DL

Teste realizado em 22/10/2026 com a versão **2.3.13**, instalada do PyPI em `.venv`, separadamente do planejador. Dependências opcionais estão em [requirements-moodle-dl.txt](../requirements-moodle-dl.txt).

## O que foi validado

- Serviço móvel habilitado na instituição, confirmado por consulta pública sem senha.
- Autenticação institucional pelo fluxo oficial de lançamento do aplicativo Moodle.
- Autorização explícita do usuário para guardar a chave no diretório privado do sistema, fora do OneDrive.
- Leitura e download limitados a uma matéria.
- Coleta de 36 PDFs, um DOCX e três atalhos URL. Atalhos são referências, não vídeos ou páginas externas integralmente baixados.
- Uma nova execução concluída sem fila de download: zero arquivos novos, alterados ou removidos, comparando hashes de todos os 40 arquivos.
- Importação dos 35 recursos de arquivo do inventário para a biblioteca organizada por aula. Os dois PDFs adicionais eram anexos de uma atividade, preservados no diretório do coletor.
- Repetição do importador com zero cópias novas e 35 recursos reaproveitados.

O Google continua com a amostra de cinco fontes da matéria testada. Os outros 30 recursos já estão baixados na biblioteca e aparecem como candidatos na prévia; nenhum envio adicional foi feito durante o teste do coletor.

## Instalação reproduzível

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-moodle-dl.txt
```

O teste também salvou uma lista privada das versões de todas as dependências instaladas. Não foi necessário instalar ferramentas de vídeo para coletar esses documentos.

## Autenticação

O pacote oferece um assistente SSO. Neste teste, o retorno do fluxo oficial foi recebido por uma página local do projeto, sem enviar a chave pela conversa e sem gravá-la no OneDrive.

O auxiliar [moodle_local_auth.py](../tools/moodle_local_auth.py) escuta somente em `127.0.0.1`, exige um nonce imprevisível do formulário e valida a chave diretamente na instituição antes de salvar. A página fecha o servidor após sucesso ou em dez minutos. O navegador embutido usa origem opaca; essa condição é tratada sem liberar CORS, mantendo o nonce obrigatório.

O diretório privado recebeu uma ACL de acesso apenas ao usuário. Não foi guardado o token privado adicional usado para gerar cookies de sessão. Não houve registro de protocolo no Windows nem acesso à senha institucional.

## Executar o teste novamente

Depois de configurar a autorização, a execução é:

```powershell
$collectorState = Join-Path $env:LOCALAPPDATA 'MoodleStudySync\moodle-dl'
.\.venv\Scripts\python.exe tools\test_moodle_dl.py --state-dir $collectorState --expected-course-id ID_DA_MATERIA --output private\collector-repeat.json
```

Substituir `ID_DA_MATERIA` pelo ID selecionado na configuração privada. O programa recusa configurações que incluam outras matérias, entregas de alunos, discussões ou coleta por cookies. Ele ativa UTF-8 e o suporte a caminhos longos do Windows, compara os arquivos antes/depois e grava uma saída com a chave redigida.

Para trazer os recursos para a biblioteca:

```powershell
.\.venv\Scripts\python.exe tools\import_moodle_dl.py --state-dir $collectorState --inventory private\inventory.json --semester 'Semestre de exemplo'
.\.venv\Scripts\python.exe -m moodle_study_sync --inventory private\inventory.json --output private\next-plan.json
```

O importador abre o catálogo do Moodle-DL somente para leitura, seleciona os IDs de recursos do inventário e verifica o hash das cópias. Versões diferentes ganham outro caminho, preservando o arquivo anterior. A compatibilidade do catálogo está validada para a versão fixada; versões futuras precisam de nova verificação.

## Limites atuais

O teste demonstra coleta real e sua repetição, não uma rotina agendada. Expiração ou revogação da autorização exigirá novo login. O próximo conector deve ler o estado do Google e confirmar cada importação antes de registrar o envio como concluído.
