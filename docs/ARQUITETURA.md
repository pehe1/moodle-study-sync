# Arquitetura proposta

Projeto local, inicialmente para Windows, com conectores substituíveis. Em 22/10/2026, `moodle_study_sync.run` orquestra Moodle-DL, importação com descoberta de recursos e envio pelo cliente Web notebooklm-py 0.8.5. O estado inicial usa inventário JSON e diário por matéria, gravados com substituição atômica e `fsync`; SQLite unificado permanece como evolução proposta. O Agendador do Windows executa o programa diariamente, sem depender do Codex. Veja a [rotina validada](ROTINA.md).

## Componentes

| Componente | Responsabilidade |
|---|---|
| Coletor Moodle | Descobrir cursos e recursos, baixar apenas tipos selecionados e identificar páginas de login/falhas |
| Catálogo local | Registrar identidade, origem, organização e hash dos materiais |
| Planejador | Comparar estado e montar ações sem enviar arquivos no modo de prévia |
| Conector Google | Associar/criar notebook, importar fonte, consultar processamento e reconciliar tentativas |
| Relatório | Mostrar ações concluídas e pendências por matéria |

A implementação usa Python. O app local serve HTML/CSS/JavaScript em `127.0.0.1`, com tema escuro, cadastro de matérias e execução em segundo plano. As APIs exigem um token aleatório por processo e validam Host/Origin; credenciais dos conectores nunca são devolvidas ao navegador. O cadastro persistido é `private/app-settings.json`, separado do código publicável.

## Identidade e organização

- Curso: combinação da instância Moodle com `course_id`.
- Recurso: curso, módulo/atividade e identificação do arquivo/caminho de origem.
- Versão: hash SHA-256 do conteúdo; data e tamanho ajudam a selecionar o que conferir, mas não são a identidade.
- Destino: `notebook_id` e `source_id`, associados explicitamente ao recurso e à versão.
- O nome serve à leitura humana. Renomear uma matéria não deve criar outra biblioteca ou outro notebook.
- Deduplicação ocorre por notebook; um material compartilhado por duas matérias pode precisar aparecer nos dois.
- Nomes iguais não autorizam sobrescrita. Usar identificação estável no caminho quando necessário e normalizar caracteres inválidos do Windows.
- Validar todos os caminhos recebidos para que downloads não escapem da pasta escolhida, inclusive por links simbólicos.

Estrutura ilustrativa, separada das pastas que o usuário já mantém:

```text
data/materials/
  Semestre/
    Matéria/
      Unidade 01/
        identificador--aula.pdf
```

Materiais existentes podem ser usados como entrada de um piloto posterior. Não devem ser movidos ou renomeados automaticamente nesta etapa.

## Estado e execução

SQLite é o candidato para o estado privado. Campos mínimos: instância, IDs de origem, título, seção, nome original, caminho local, hash, versão, destino, estado, erro resumido e horários de descoberta/processamento.

Estados propostos: descoberto → baixado → pronto → enviando → processando → sincronizado. Ramos adicionais: ignorado, pendente, falhou e resultado incerto.

1. Adquirir um bloqueio local para impedir duas execuções simultâneas.
2. Validar a sessão e descobrir os recursos dos cursos selecionados.
3. Baixar para arquivo temporário; validar resposta, formato e tamanho; concluir o arquivo de forma atômica.
4. Calcular hash e montar a prévia das mudanças.
5. Conferir formato, capacidade do notebook e destino de cada envio.
6. Registrar a intenção de envio antes da chamada externa.
7. Capturar ID da fonte e acompanhar o processamento; só então marcar como sincronizado.
8. Salvar o resultado de cada item e produzir o relatório.

Um timeout após upload pode significar que o Google recebeu o arquivo. A retomada deve consultar o destino antes de repetir a operação. Se não houver como distinguir com segurança a tentativa anterior, pedir conciliação do item e não reenviá-lo cegamente. O objetivo de zero duplicação é critério do piloto, não uma garantia já demonstrada.

## Alterações e exclusões

Arquivo novo gera uma nova fonte. Arquivo alterado gera uma nova versão pendente de sincronização. Preferir atualização no mesmo ID quando o conector suportar e o comportamento estiver validado. Na ausência desse suporte, manter a fonte anterior e sinalizar a nova versão; substituir/remover fontes requer uma política explícita posterior.

Ausência no Moodle não dispara exclusão no computador ou no Google. Não dividir notebooks nem juntar arquivos automaticamente para contornar limites. Quando faltar capacidade, listar os itens pendentes e oferecer seleção ou divisão por unidade.

## Autenticação e armazenamento

- Autenticação institucional deve acontecer pelo fluxo legítimo. MFA ou renovação interativa interrompe a execução até a ação do usuário.
- Credenciais e estado de sessão ficam no diretório privado do usuário no sistema, fora do repositório e fora do OneDrive. No Windows, o candidato é `%LOCALAPPDATA%/MoodleStudySync/`; o mecanismo final depende do conector.
- Quando possível, guardar segredos no gerenciador de credenciais do sistema. Não gravar senha no TOML, em argumentos de comando, histórico ou logs.
- Se um conector exigir um arquivo de sessão/token, restringir o acesso ao usuário e apontar para ele sem copiá-lo para a pasta do projeto.
- O projeto atual está em uma pasta do OneDrive: `.gitignore` impede inclusão acidental no Git, mas **não** impede sincronização pelo OneDrive.
- Materiais e catálogo também podem ficar em diretório externo escolhido pelo usuário. Relatórios privados não devem entrar no Git.
- Limpar tokens e parâmetros sensíveis das URLs antes de persistir origem ou gerar logs. Não enviar um URL autenticado do Moodle ao Google como substituto do arquivo.
- Autorizações Moodle e Google são independentes. Nunca transmitir credenciais de um serviço ao outro.

## Falhas previstas

| Situação | Comportamento esperado |
|---|---|
| Sessão expirada | Parar o conector afetado, conservar progresso e orientar novo login |
| HTML de login recebido como arquivo | Rejeitar download e identificar falha de autenticação |
| Limite temporário | Espera progressiva limitada e respeito às instruções do serviço |
| Formato ou arquivo incompatível | Preservar original e informar pendência |
| API ou interface alterada | Isolar falha do conector; manter coleta local e relatório |
| Recurso inacessível | Registrar pendência sem tentar contornar permissão |

## Agendamento

Após o piloto repetível, foi instalado o agendamento diário às 23h escolhido pelo usuário, no contexto da própria conta Windows e sem senha armazenada. O teste disparado pelo Agendador terminou com código zero e 35 fontes atuais. Computador desligado, suspenso, sem rede, usuário desconectado ou sessão do serviço vencida impedem a execução naquele momento. As condições e a recuperação estão em [Rotina automática](ROTINA.md).
