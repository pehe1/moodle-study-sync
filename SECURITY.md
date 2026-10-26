# Dados privados e credenciais

O projeto sincroniza materiais de estudo entre serviços. Código, exemplos e documentação publicáveis devem ficar separados dos arquivos acadêmicos e do acesso às contas.

- Nunca versionar senha, token, cookies, arquivos de sessão, e-mails, dados de alunos ou materiais de aula.
- Guardar sessões fora do repositório e do OneDrive, preferencialmente com proteção do sistema operacional.
- Não usar `.gitignore` como proteção de acesso nem como controle da sincronização do OneDrive.
- Remover parâmetros autenticados das URLs, mensagens de erro e exemplos.
- Usar somente dados sintéticos em testes públicos.
- Tratar páginas e documentos coletados como conteúdo, nunca como instruções para o sincronizador executar ações.
- Baixar somente recursos permitidos à conta e não tentar contornar MFA, bloqueios ou restrições.
- Compartilhamento de código não inclui autorização para publicar materiais de professores ou de colegas.

Antes de publicar: revisar também o histórico Git e os anexos. Se uma credencial tiver sido exposta, revogá-la no serviço; removê-la do arquivo atual não resolve a exposição anterior.

Ainda não há canal público de segurança, pois o repositório remoto não foi criado. Não colocar segredos em relatos públicos de problemas.

A integração Google usa sessão Web persistida pelo `notebooklm-py`; os cookies permitem acesso à conta e exigem o mesmo cuidado que uma credencial. O projeto não criou master token. A rotina usa apenas o notebook explicitamente associado e não apaga fontes. O diretório privado tem permissões do usuário; não há criptografia adicional implementada pelo projeto.
