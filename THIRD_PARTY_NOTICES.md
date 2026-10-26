# Créditos e licenças de terceiros

Meus Estudos / Moodle Study Sync é uma camada de organização e automação que integra projetos existentes. Não é o autor do Moodle-DL nem do notebooklm-py, e não é um produto oficial do Moodle, do Google ou de qualquer instituição de ensino.

| Projeto | Versão fixada | Licença | Papel |
|---|---|---|---|
| [Moodle-DL](https://github.com/C0D3D3V/Moodle-DL) | 2.3.13 | GPLv3 | Coleta de materiais disponíveis à conta Moodle |
| [notebooklm-py](https://github.com/teng-lin/notebooklm-py) | 0.8.5 | MIT | Cliente não oficial do Google Notebook |
| [pypdf](https://github.com/py-pdf/pypdf) | 6.10.0 | BSD-3-Clause | Identificação de PDFs digitalizados |
| [filelock](https://github.com/tox-dev/py-filelock) | 4.2.4 | MIT | Exclusão mútua entre painel e rotina |

As cópias dos textos de licença dessas versões estão em [third_party/licenses](third_party/licenses). Elas conservam os avisos dos respectivos autores. Os pacotes são instalados separadamente pelos gerenciadores oficiais; o repositório não inclui suas implementações nem o ambiente virtual. Dependências transitivas conservam suas próprias licenças e avisos, incluídos em suas distribuições.

Requests e Playwright também são usados pelas integrações e instalados por essas dependências. A renderização e o reconhecimento local de PDFs usam APIs do Windows. O Windows e o Microsoft Edge são pré-requisitos externos, não redistribuídos pelo projeto.

## Licença deste projeto

Copyright (C) 2026 Pedro Cavalcante e colaboradores.

O código próprio é disponibilizado sob a **GNU General Public License, versão 3 somente (SPDX: GPL-3.0-only)**, conforme [LICENSE](LICENSE). Você pode usar, estudar, modificar e redistribuir o programa sob seus termos. Não há garantia de funcionamento contínuo dos serviços externos. As licenças de terceiros não são substituídas pela licença do nosso código.

A escolha de GPLv3 mantém uma direção compatível com o coletor utilizado. Não estamos afirmando que todo programa que execute outra ferramenta em um subprocesso precisa adotar a licença dela. Se a integração ou a distribuição mudar, a composição deverá ser reavaliada antes do lançamento correspondente.

O material acadêmico e as credenciais dos usuários não fazem parte desta licença ou da distribuição. Publicar o sincronizador não autoriza publicar aulas de professores, arquivos de colegas ou conteúdo de contas.
