# Escopo inicial

Versão 0.1 — 22/10/2026. Proposta revisável, anterior à implementação.

## Problema e resultado esperado

Os materiais de estudo chegam ao Moodle separados por disciplinas e atividades, mas baixar, conferir novidades e alimentar uma ferramenta de estudo exige trabalho repetitivo. O projeto deve preservar essa organização e reduzir esse trabalho.

Resultado: uma biblioteca por matéria, com origem rastreável, e um notebook de estudo correspondente, atualizado com os materiais selecionados.

## O que já sabemos

- O usuário estuda em um Moodle e acessa com conta institucional.
- Há cinco pastas de matérias no diretório local do quinto semestre.
- O destino do piloto é uma conta Google pessoal. O acesso ao Notebook foi confirmado e a interface exibia o selo PRO e limite de 300 fontes; capacidades futuras devem ser consultadas novamente.
- O endereço e os nomes locais estão na configuração privada, fora dos arquivos destinados à publicação.
- O acesso institucional e a API móvel foram confirmados na conta do usuário. O Moodle-DL foi validado em uma matéria e trouxe os recursos para a biblioteca. Oito PDFs foram enviados ao Google nos pilotos pelo navegador; a integração programática de upload continua pendente.

## Organização proposta

| Origem | Biblioteca local / Drive opcional | Google Notebook |
|---|---|---|
| Curso no Moodle | Pasta com o nome confirmado da matéria | Notebook com esse mesmo nome |
| Seção, unidade ou semana | Subpasta correspondente | Prefixo da fonte; rótulos se disponíveis |
| Arquivo ou página | Original e metadados de origem | Fonte compatível |

Um notebook por matéria é a unidade inicial de estudo. O semestre fica nos metadados e na organização local. Se houver matérias homônimas em períodos diferentes, o sistema deve pedir a associação correta e preservar os IDs; nunca juntar automaticamente por semelhança de nome.

## Primeira versão utilizável

1. **Acesso:** autenticação pelo mecanismo permitido pela instituição; primeira entrada e eventual renovação podem precisar do usuário.
2. **Descoberta:** listar as matérias acessíveis e selecionar explicitamente as desejadas.
3. **Mapeamento:** associar o ID do curso ao nome local e ao ID do notebook.
4. **Coleta:** priorizar PDF, DOCX, PPTX, TXT e Markdown; validar formatos efetivamente aceitos no destino. Páginas de aula podem virar Markdown com título e origem.
5. **Biblioteca:** preservar o original, a seção e a identificação do recurso; evitar colisões de nomes e sobrescrita de materiais existentes.
6. **Prévia:** mostrar o que será baixado, enviado, mantido ou marcado como pendente.
7. **Envio:** criar ou associar o notebook e importar as fontes selecionadas; confirmar o processamento antes de registrar sucesso.
8. **Atualização:** detectar novidades e versões modificadas; nova execução sem mudanças não deve repetir uploads.
9. **Recuperação:** retomar falhas e apresentar a ação necessária quando sessão ou cota impedir a execução.
10. **Resumo:** informar por matéria quantos itens foram encontrados, baixados, enviados, ignorados e ficaram pendentes.

## Limites da primeira versão

- Coleta de materiais didáticos acessíveis ao usuário. Notas, participantes, mensagens, fóruns, tentativas de provas e entregas de trabalhos ficam fora da coleta padrão.
- Arquivos externos que exigem outro login ficam como pendência identificada. Um link para um anexo não conta como conteúdo importado.
- ZIP, executáveis e formatos sem suporte são preservados/relatados, sem envio automático. Conversão, OCR e transcrição ficam para etapas posteriores.
- Nenhuma exclusão automática de materiais locais, fontes ou notebooks.
- Agendamento vem depois do fluxo manual validado. Não haverá promessa de login permanente.
- Geração de resumos, flashcards, simulados e plano de estudos é uma evolução após a ingestão confiável.
- Aplicativo web, serviço hospedado e suporte a várias contas ficam fora do piloto.

## Critérios de sucesso do piloto

Escolher uma matéria com amostra de 5 a 10 itens, quando disponíveis, incluindo um PDF, uma apresentação e uma página de aula.

- Todos os itens elegíveis da amostra aparecem na matéria correta, com origem identificável.
- Cada formato usado no piloto abre e é processado no destino.
- O usuário consegue fazer uma pergunta de estudo e conferir a referência ao material enviado.
- Duas execuções consecutivas sem mudanças criam **zero fontes duplicadas**.
- Um arquivo novo e uma versão alterada são reconhecidos corretamente, usando dados sintéticos quando não houver mudança real.
- Uma interrupção de envio pode ser retomada sem repetir as fontes já confirmadas.
- Sessão expirada, limite atingido e formato incompatível geram pendência compreensível.
- Os materiais locais preexistentes continuam intactos.
- Credenciais, arquivos acadêmicos e metadados privados ficam fora dos arquivos versionados.

## Decisões que dependem do piloto

O fluxo real de autenticação institucional; disponibilidade dos serviços móveis; conector Google; limites da conta; política de versões substituídas; necessidade de Drive; frequência da sincronização; licença e publicação do projeto.
