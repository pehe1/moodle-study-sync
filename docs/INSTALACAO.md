# Instalação experimental no Windows

Esta versão foi validada em Windows com Python 3.14 e Microsoft Edge. Ainda não há instalador para o público geral nem assistente completo para o primeiro acesso Moodle de outra instituição. O cadastro de matérias e semestres funciona pelo app depois da configuração inicial dos conectores.

## Preparar o ambiente

Use Python 3.11 ou posterior e mantenha o projeto em uma pasta local. Fora de pastas sincronizadas, há menos interferência de arquivos em uso e cópias de conflito. Dentro da pasta do projeto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-moodle-dl.txt -r requirements-google.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

O ambiente virtual não deve ser incluído no Git ou redistribuído junto com o código. A instalação pelo pip conserva os avisos das dependências.

## Primeiros acessos

1. Escolha um diretório privado fora do projeto e de serviços de sincronização, como `%LOCALAPPDATA%\MoodleStudySync`. Restrinja o acesso à sua conta Windows. Nunca copie a configuração de outro usuário.
2. Configure o Moodle-DL nesse diretório, em `moodle-dl/`, seguindo o [assistente oficial](https://github.com/C0D3D3V/Moodle-DL). Consulte `.\.venv\Scripts\moodle-dl.exe --help`. A instituição precisa permitir os serviços móveis utilizados pelo coletor. Login institucional e MFA devem ser feitos por você.
3. Limite a coleta aos recursos de arquivo das matérias escolhidas. Entregas, discussões, notas e cookies do navegador não pertencem ao escopo deste projeto. O programa atualiza a lista de cursos permitidos a partir das matérias ativas.
4. Execute `Conectar-Google.cmd` para entrar no Google no navegador. A sessão será guardada no diretório privado. Nenhuma senha deve entrar no código ou em arquivos de exemplo.
5. Abra `Meus-Estudos.cmd`. Uma instalação nova começa com biblioteca vazia. Atualize o catálogo depois de conectar as contas e cadastre as matérias. A reconexão Moodle no app pressupõe que o endereço inicial já foi configurado.

Se usar um diretório privado diferente do padrão, informe `MOODLE_STUDY_SYNC_HOME` antes de executar os comandos e forneça o mesmo caminho a `tools/Install-Schedule.ps1 -PrivateHome CAMINHO_PRIVADO`. A tarefa registra apenas o caminho e o horário em `private/runtime.local.json`, sem copiar credenciais. A reconexão Moodle atual utiliza esse arquivo de localização.

## Agendamento e limites

Depois de validar uma atualização manual, instale a tarefa do usuário:

```powershell
.\tools\Install-Schedule.ps1 -PrivateHome CAMINHO_PRIVADO -DailyAt '23:00'
```

O computador precisa estar ligado, com internet e com sua sessão Windows aberta. O cliente Google é não oficial; mudanças no serviço ou sessão vencida podem interromper a rotina. O limite de fontes depende da conta: a instalação nova usa 50, e qualquer aumento deve corresponder ao plano real.

Somente os tipos suportados entram no notebook. Os demais ficam locais. Uma fonte anterior ao projeto pode ser preservada sem comprovação dos bytes. O programa conserva versões e não apaga fontes. Quando um envio tem confirmação incerta, exige conferência em vez de repetir silenciosamente.

Para dúvidas sobre distribuição e atribuição, veja [créditos](../THIRD_PARTY_NOTICES.md). Não envie materiais acadêmicos, cookies ou tokens em issues e pull requests.
