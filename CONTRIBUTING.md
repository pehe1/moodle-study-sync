# Como contribuir

O projeto tem uma versão experimental para Windows, com coleta de várias matérias, app local e agendamento. Leia o [README](README.md), a [pesquisa](docs/PESQUISA.md) e os [créditos](THIRD_PARTY_NOTICES.md) antes de alterar um conector.

Contribuições úteis nesta fase:

- Relatos de compatibilidade com versão do Moodle e mecanismo de login, sem dados de conta.
- Comparação reproduzível entre conectores existentes.
- Exemplos sintéticos de cursos, seções, arquivos e falhas.
- Melhorias na experiência de organização e no relatório de sincronização.

O código público deve ser independente de uma faculdade. Endereços reais, nomes de turmas, IDs de notebooks e credenciais pertencem à configuração local.

Não copie código de outro projeto sem identificar licença e atribuição. O código próprio usa GPL-3.0-only; as dependências conservam suas licenças. Contribuições ao projeto devem ser compatíveis com essa licença. Não afirmar que somos autores dos conectores usados.

Toda mudança deve explicar o comportamento observado e demonstrar o caso afetado com dados sintéticos. Execute `python -m unittest discover -s tests -v` no ambiente do projeto. Testes de integração reais são opcionais e devem usar somente uma conta ou conjunto explicitamente selecionado. A automação de PDFs usa APIs locais do Windows; outros sistemas ainda não foram validados.
