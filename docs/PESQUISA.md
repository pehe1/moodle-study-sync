# Pesquisa de integração e reaproveitamento

Consulta realizada em 22/10/2026. As funcionalidades abaixo são documentadas pelas respectivas fontes. Depois da pesquisa inicial, o Moodle-DL 2.3.13 foi validado na instituição com autenticação real, coleta de uma matéria e repetição sem downloads. Os pilotos Google usaram o navegador; clientes programáticos Google continuam por validar.

## Fatos que orientam o desenho

**Produto Google.** A mudança de nome para Gemini Notebook foi anunciada em julho de 2026. [Anúncio oficial](https://blog.google/innovation-and-ai/products/gemini-notebook/notebooklm-gemini-notebook/).

**Moodle.** Serviços web dependem de configuração e permissões do site. A existência de um login de aluno não garante acesso por API. O serviço móvel é o caminho a testar antes de desenvolver coleta pelo navegador. [Serviços móveis](https://docs.moodle.org/en/Mobile_web_services), [configuração de serviços web](https://docs.moodle.org/en/Using_web_services).

**API Google.** Foi localizada documentação oficial de criação de notebooks e fontes para o produto Enterprise, com projeto Google Cloud e controle de acesso próprios. Não foi localizada nesta pesquisa uma API pública equivalente para a conta comum. Uma assinatura de uso pessoal não deve ser presumida como acesso Enterprise. [Notebooks](https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-notebooks), [fontes](https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-notebooks-sources).

**Drive.** A documentação descreve atualização de fontes já importadas do Drive. Isso não demonstra descoberta automática de arquivos novos em uma pasta; a inclusão inicial de cada fonte continua sendo uma operação do projeto. Tipos e limites devem ser conferidos durante o piloto. [Ajuda oficial de fontes](https://support.google.com/gemininotebook/answer/16215270?hl=en).

**Integrações prontas.** A busca no catálogo conectado por Moodle, NotebookLM e Gemini Notebook não retornou um plugin específico útil nesta sessão. O resultado não prova inexistência de outras integrações.

## Projetos encontrados

| Projeto | O que documenta | Limite para este objetivo | Uso proposto |
|---|---|---|---|
| [C0D3D3V/Moodle-DL](https://github.com/C0D3D3V/Moodle-DL) | Download incremental de materiais e configuração por curso; usa API móvel e oferece fluxo SSO | Precisa funcionar com o Moodle institucional; coleta ampla deve ser restringida | Primeiro candidato para a etapa de coleta |
| [paladini/extract-moodle-content-to-notebook-lm-extension](https://github.com/paladini/extract-moodle-content-to-notebook-lm-extension) | Captura durante a navegação e exportação por curso em Markdown; licença MIT | Não demonstra sincronização integral de anexos e uploads recorrentes; links exigem tratamento separado | Alternativa para conteúdo de páginas quando API não estiver disponível |
| [YairHazan12/moodle-to-notebooklm](https://github.com/YairHazan12/moodle-to-notebooklm) | Extração e exportação de conteúdo, tentativas de integração visual e envio ao Drive | Documenta etapas assistidas e dependência da interface; não foi encontrada licença na raiz consultada e o GitHub não identificou uma | Referência funcional; não incorporar código sem esclarecer licença |
| [teng-lin/notebooklm-py](https://github.com/teng-lin/notebooklm-py) | Cliente Python/CLI não oficial para notebooks e fontes; licença MIT | Usa interfaces não documentadas do Google, sujeitas a alterações | Candidato experimental para upload, isolado do restante do sistema |

A licença GPL-3.0 aparece no README e nos metadados do Moodle-DL. A forma de integrar e distribuir componentes precisa ser definida antes da licença do nosso projeto. Foram instalados Moodle-DL 2.3.13 e notebooklm-py 0.8.5 como dependências; não foi copiado código de implementação desses repositórios.

## Opções para o destino

| Caminho | Potencial de automação | Dependência principal | Prioridade |
|---|---|---|---|
| Cliente não oficial isolado | Criação e envio automáticos após autenticação, se o piloto funcionar | Sessão e compatibilidade do cliente | Testar com uma amostra |
| Interface do navegador | Automatiza ações visíveis, com login interativo quando necessário | Mudanças da interface e disponibilidade da sessão | Alternativa se o cliente falhar |
| Drive + inclusão de fontes | Upload de arquivos por API; inclusão no notebook deve ser resolvida separadamente | OAuth e compatibilidade da importação | Plano de continuidade |
| API Enterprise oficial | Integração documentada | Acesso Enterprise, projeto e permissões | Considerar apenas se a conta já tiver acesso adequado |

## Recomendação

Começar como uma camada pequena de integração, com coleta, registro de estado e destino separados. Avaliar o Moodle-DL antes de desenvolver outro baixador. Comparar o piloto de upload com o cliente não oficial e uma alternativa assistida. A escolha deve usar evidência de funcionamento na conta real.

Se uma solução existente já atender aos critérios do piloto, preferir configurá-la ou contribuir com ela. Um repositório próprio se justifica pela parte ainda não demonstrada: associação estável matéria/notebook, sincronização sem duplicação, retomada e uma experiência simples em português.

## Pendências da instituição

O acesso institucional foi validado pelo fluxo normal de login e pelos serviços móveis com a conta do aluno. Moodle-DL coletou a matéria selecionada, e notebooklm-py enviou os arquivos à conta Google autorizada. A repetição completa não criou duplicatas. Sessões futuras e mudanças nos serviços continuam sendo limites de operação; veja a [rotina validada](ROTINA.md).
