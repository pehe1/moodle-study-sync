# Rotina automática

## Validação em 22/10/2026

Na matéria piloto, o Google tinha cinco fontes. Um envio programático acrescentou uma fonte e o lote seguinte acrescentou 29. Todos os 35 recursos foram confirmados como processados, incluindo um arquivo Word. A execução completa seguinte retornou `current: 35`, sem envios. Uma execução disparada pelo próprio Agendador terminou com código zero e o mesmo resultado.

O agendamento local está ativo diariamente às **23h, horário de Brasília**. Se o computador perder o horário, `StartWhenAvailable` permite tentar depois. É necessário estar ligado, conectado e com a sessão do mesmo usuário aberta. Não requer o Codex aberto. A primeira execução diária futura ainda depende dessas condições; o teste foi disparado manualmente pelo Agendador.

Os títulos dos novos materiais são organizados automaticamente a partir do nome da aula no Moodle, preservando acentos e removendo espaços extras e quebras de linha. Se a aplicação do título falhar, a próxima execução tenta concluir a renomeação no mesmo arquivo, sem novo upload. Renomeações manuais posteriores são preservadas.

## Expansão para várias matérias

O app mantém seis matérias, reunindo dez salas de teoria/prática. O agendamento existente conserva o nome histórico `MoodleStudySync-Empreendedorismo`, mas agora executa todas as salas ativas de `private/app-settings.json`. A primeira execução diária real ocorreu em 22/10 às 23h e sinalizou duas plantas PDF recusadas pelo Google; o painel apresenta pendências por arquivo. O diagnóstico atual está sempre em `private/last-sync.json` e na biblioteca do app.

## Uso no computador configurado

- Abra o atalho **Meus Estudos** para gerenciar matérias e semestres; veja [APP.md](APP.md).
- Abra `Atualizar-agora.cmd` para antecipar uma atualização.
- Abra `private/status.html` para ver a situação e acessar o notebook.
- Abra `Conectar-Google.cmd` se for necessário renovar a sessão Google.
- A tarefa Windows se chama `MoodleStudySync-Empreendedorismo`; pode ser desabilitada no Agendador.

Consulte o painel para novidades e pendências. A execução sem janela grava `private/last-scheduled.json` e o relatório de sincronização; não envia e-mails. O wrapper PowerShell antigo conserva suporte a avisos locais para execuções manuais.

## Executar e configurar

Use Python 3.11 ou posterior (piloto: 3.14.6). Crie um ambiente virtual e instale as dependências fixadas em `requirements-moodle-dl.txt` e `requirements-google.txt`. O cliente Google é **não oficial** e usa o transporte Web; não há promessa de compatibilidade permanente.

Para o primeiro cadastro manual, copie `sync.example.toml` para `sync.local.toml` e indique as matérias habilitadas e seus inventários. Depois, o app importa essa configuração para `private/app-settings.json`. Novos cadastros devem ser feitos pelo app. O inventário precisa identificar o notebook por ID e título e os recursos por IDs Moodle. Materiais não podem apontar para fora do projeto. O limite de fontes deve corresponder ao plano da conta (piloto: 300).

```powershell
.\.venv\Scripts\python.exe -m moodle_study_sync.run --max-uploads 35
# Etapas isoladas para diagnóstico:
.\.venv\Scripts\python.exe -m moodle_study_sync.run --collect-only
.\.venv\Scripts\python.exe -m moodle_study_sync.run --google-only --max-uploads 0
```

`--max-uploads 0` não cria fontes; ainda consulta o Google, concilia recibos de envios anteriores e pode concluir a organização dos títulos de fontes criadas pelo projeto. A prévia totalmente offline continua disponível em `python -m moodle_study_sync`.

## Estado e credenciais

`private_home()` usa o diretório privado do usuário. No Windows, normalmente é `%LOCALAPPDATA%\MoodleStudySync`. A chave Moodle fica em `moodle-dl/config.json`; a sessão Google em `google/profiles/study-sync/storage_state.json`. As pastas têm ACL restrita ao usuário. Não são criptografadas pelo projeto; não mover para OneDrive nem versionar.

Aplicativos Windows empacotados podem redirecionar AppData. Por isso o instalador grava o caminho físico em `private/runtime.local.json` e a tarefa o fornece explicitamente por `MOODLE_STUDY_SYNC_HOME`. O arquivo contém o caminho, nunca a chave ou os cookies. O teste pelo Agendador validou o acesso fora do processo do Codex.

`tools/Install-Schedule.ps1 -PrivateHome CAMINHO_PRIVADO` registra a tarefa do usuário, sem privilégios administrativos, sem armazenar a senha do Windows e sem alterar a política de execução. A tarefa usa `pythonw.exe -m moodle_study_sync.scheduled`, sem janela e sem depender da inicialização do PowerShell. Existe um lock do programa e a tarefa ignora execuções sobrepostas.

## Como evita duplicações

Antes de criar uma fonte, o diário `private/google-journal-<curso>.json` registra a intenção de envio. Depois que os bytes foram transferidos, salva o ID retornado, espera o processamento e persiste o recibo com hash e notebook. Títulos legíveis são aplicados ao mesmo ID, sem criar novas fontes.

Se o processamento demorar, a execução seguinte consulta o mesmo ID. Se houver dúvida sobre a confirmação do envio, o programa para para revisão e não cria outra fonte automaticamente. Um título coincidente sozinho nunca comprova que o conteúdo foi enviado. Fontes acrescentadas manualmente são preservadas.

Novas versões são enviadas como novas fontes e o histórico anterior é mantido, pois não há autorização para exclusões automáticas. Fontes removidas manualmente do Google não são recriadas silenciosamente. Quando um recurso é retirado do Moodle, a biblioteca local é preservada.

## Limites atuais

- Apenas recursos Moodle do tipo arquivo (`resource`) entram automaticamente no notebook. Atalhos externos e anexos de atividades não fazem parte da sincronização.
- A descoberta usa o catálogo atualizado do Moodle-DL da matéria permitida. Mudanças na instituição, permissão ou autenticação podem impedir a coleta.
- Todas as salas ativas são incluídas automaticamente na lista permitida do Moodle-DL antes da coleta. Uma falha de envio em uma sala não impede conferir as demais.
- O login Google Web pode vencer. A rotina tenta a renovação suportada pelo cliente; se falhar, precisa de uma nova entrada interativa. Não foi criado master token nem adotado o backend Android.
- Os testes cobrem repetição, deduplicação de conteúdo, nova versão, remoção remota, timeout no processamento e resultado de upload incerto. Não demonstram recuperação sem intervenção de toda falha possível.

Documentação primária do cliente: [instalação 0.8.5](https://github.com/teng-lin/notebooklm-py/blob/v0.8.5/docs/installation.md), [API e idempotência](https://github.com/teng-lin/notebooklm-py/blob/v0.8.5/docs/python-api.md), [CLI e sessões](https://github.com/teng-lin/notebooklm-py/blob/v0.8.5/docs/cli-reference.md).

## Arquivos especiais e fontes anteriores

Formatos de laboratório sem suporte permanecem locais, com contagem no cartão da matéria. PDFs digitalizados podem ser convertidos em texto pelo reconhecimento local do Windows. Se um PDF de uma página não tiver texto suficiente e for recusado pelo Google, a alternativa é uma imagem PNG da página completa. Essa alternativa não descarta páginas de PDFs maiores. O original é preservado. Os recibos distinguem o hash do original, o hash enviado e a representação (`ocr-text` ou `pdf-image`).

Quando uma fonte anterior ao projeto é identificada por ID ou título único, o estado é `existing-preserved`: uma referência local inicial, **sem comprovar os bytes do conteúdo remoto**. Esse estado não serve de recibo para deduplicar outra sala. Fontes com erro de processamento ficam preservadas no Google; o programa não as apaga automaticamente.

## Verificação de 23/10/2026

A planta recusada foi aceita como imagem e associada às salas de teoria e prática sem duplicar o conteúdo. A repetição pelo próprio Agendador terminou com código zero e nenhum upload novo. Foram conferidos o tema escuro, as telas de contas/cadastro e 34 testes automatizados. O controle de concorrência agora conserva o arquivo `private/sync-v2.lock` entre execuções: a posse depende do bloqueio do Windows, e não da existência do arquivo. Isso evita o estado de exclusão pendente observado no arquivo de controle anterior.

## Recursos com vários arquivos e execução direta

Um recurso Moodle pode trazer vários arquivos, como exercícios e gabarito. O importador usa o ID do recurso e a identidade do arquivo para preservar recibos separados; conteúdo repetido ainda pode compartilhar uma fonte verificada. O lançador do Agendador foi alterado para Python sem janela depois de uma inicialização PowerShell permanecer parada sem iniciar a coleta. O horário e as permissões de usuário foram preservados.
