# Entregas e backlog

Situação inicial em 22/10/2026. As etapas são sequenciais, sem estimativa de prazo antes de validar o acesso.

## Etapa 0 — Escopo

- [x] Registrar objetivo e limites da primeira versão.
- [x] Localizar projetos comparáveis e documentação primária.
- [x] Receber endereço da instituição e informação sobre login.
- [x] Preparar arquitetura, plano de validação e configuração ilustrativa.
- [x] Separar dados específicos do usuário dos arquivos publicáveis.
- [x] Conferir acesso à conta Google e limites exibidos na interface do piloto.

## Etapa 1 — Prova de acesso e coleta

- [x] Identificar a entrada institucional: a página do Moodle encaminha ao login Microsoft Office 365 por OIDC.
- [x] Concluir o login institucional realizado pelo usuário; sessão autenticada confirmada no navegador.
- [ ] Verificar renovação de sessão e necessidade de MFA nas execuções futuras.
- [x] Conferir serviços móveis e capacidade de leitura disponíveis ao aluno, com autenticação real.
- [x] Escolher uma matéria para piloto e associar seu ID ao nome desejado na configuração privada.
- [x] Testar Moodle-DL 2.3.13 em ambiente isolado, com uma matéria selecionada e exclusão de entregas e discussões da coleta.
- [ ] Se incompatível, avaliar a captura pelo navegador antes de criar um coletor próprio.
- [x] Catalogar os recursos de arquivo visíveis da matéria piloto e separar links externos e atividades de entrega.
- [x] Baixar uma amostra de cinco arquivos em pasta separada; conferir nomes, estrutura dos formatos e hashes das cópias.
- [ ] Conferir visualmente o conteúdo e confirmar processamento dos formatos no Google.

O coletor trouxe 36 PDFs, um DOCX e três atalhos URL. Dois anexos de atividade precisaram do suporte a caminhos longos do Windows. Após a execução completa, uma nova coleta teve fila zero e manteve todos os 40 arquivos iguais por hash. O importador associou os 35 recursos do inventário à biblioteca e, ao repetir, reaproveitou todos sem copiar arquivos novos. Esses resultados validam coleta e importação; o envio recorrente ao Google ainda é uma etapa separada.

Saída: decisão documentada sobre o coletor e uma amostra íntegra, sem mexer nas pastas existentes. A etapa pode terminar com uma limitação de acesso documentada; isso impede prometer coleta sem intervenção.

## Etapa 2 — Prova de envio

- [x] Verificar a conta Google de destino pelo login normal do usuário.
- [x] Identificar notebook existente pela disciplina e conferir a sobreposição de sete fontes; registrar IDs na configuração privada. A igualdade de versões das fontes anteriores ainda depende de verificação.
- [x] Testar envio pelo navegador com três PDFs ausentes no notebook existente.
- [x] Confirmar IDs e processamento, obter resposta com citações para as três fontes e abrir uma referência do laboratório.
- [x] Testar um formato adicional (DOCX) e registrar o limite observado da conta.
- [x] Escolher o conector e documentar suas limitações de sessão e manutenção.
- [ ] Se upload direto falhar, verificar Drive e inclusão assistida como continuidade, sem chamar essa alternativa de sincronização completa.

Saída: demonstração de upload com evidência observada e escolha de destino. Não criar estrutura de todas as matérias antes desse teste.

## Etapa 3 — Primeira versão repetível

- [x] Implementar configuração validada e mapeamento por IDs para uma matéria.
- [x] Implementar primeira prévia local, sem upload, baseada em inventário privado e recibos por notebook/hash.
- [x] Persistir recibos e diário com substituição atômica e conciliar com o estado remoto ao vivo.
- [x] Implementar ingestão com confirmação de processamento.
- [x] Tratar arquivos novos, alterações e limites de capacidade.
- [x] Retomar processamento por ID e impedir reenvio quando o resultado é incerto.
- [x] Gerar relatório em português por matéria.
- [ ] Aplicar os critérios de sucesso do escopo à amostra de 5 a 10 itens.
- [x] Expandir para seis matérias e dez salas, juntando teoria e prática conforme autorizado.
- [x] Criar app local com cadastro de semestres, notebooks, pausa e reconexão.
- [x] Aplicar tema escuro e indicar arquivos locais e pendências no painel.

Empreendedorismo teve 35 fontes confirmadas no Google, incluindo DOCX: cinco preservadas do piloto e 30 enviadas programaticamente. A repetição completa consultou o estado remoto e retornou 35 atuais, sem uploads. A execução pelo Agendador também terminou com código zero e 35 atuais. Os 23 testes cobrem, entre outros casos, falhas ambíguas de upload, retomada do processamento e descoberta de recursos novos.

Testes relevantes durante a implementação: identidade de arquivos homônimos; mudança de nome da matéria; mesmo conteúdo entre matérias; resposta de login no download; arquivo novo/alterado; timeout depois do envio; sessão vencida; capacidade esgotada; caminhos inválidos. Usar arquivos sintéticos e não gravar credenciais nas evidências.

## Etapa 4 — Rotina e estudo

- [x] Validar repetidas execuções manuais no uso real.
- [x] Definir frequência e habilitar execução agendada no computador (diariamente às 23h).
- [x] Produzir relatório local e avisos somente para novidades ou problemas novos.
- [ ] Adicionar índice por unidade e modelos de perguntas para estudar com referências.
- [ ] Avaliar flashcards, revisões e questões a partir dos materiais selecionados.

## Etapa 5 — Preparação pública

- [ ] Decidir entre contribuição a projeto existente, extensão e repositório próprio.
- [x] Escolher GPL-3.0-only para o código próprio e conservar as licenças dos conectores nos créditos.
- [ ] Fixar versões e registrar instalação reproduzível.
- [ ] Documentar limitações dos conectores e instituições testadas.
- [x] Preparar seleção pública por lista permitida, com exclusão de dados locais e cópias de conflito.
- [ ] Criar repositório remoto e publicar somente quando a direção pública estiver definida.

## Próxima tarefa concreta

Acompanhar a rotina de todas as matérias. Planejar uma versão protegida para domínio próprio, mantendo o coletor e as sessões locais enquanto não houver uma arquitetura de autenticação apropriada. Os resultados, condições de execução e recuperação estão em [Rotina automática](ROTINA.md). Não é necessário manter esta conversa aberta.
