# Primeira rotina reutilizável

O módulo `moodle_study_sync` prepara uma prévia local de sincronização. Usa apenas a biblioteca padrão do Python 3.11 ou mais recente. Não solicita senha, não acessa a rede e não faz upload.

## Executar

Na pasta do projeto, com um inventário privado existente:

```powershell
python -m moodle_study_sync --inventory private/inventory.json --output private/next-plan.json
```

O programa grava um JSON separado do inventário, com as decisões por recurso. Inventários e prévias reais devem ficar em pastas ignoradas pelo Git.

## Decisões

| Ação | Significado |
|---|---|
| `upload` | Há arquivo local elegível e ainda não há recibo de envio associado |
| `recorded_current` | Os bytes locais correspondem ao recibo processado do mesmo notebook |
| `await_download` | Recurso catalogado, ainda sem arquivo local |
| `review_existing_version` | Há associação a fonte anterior, mas a igualdade do conteúdo não foi demonstrada |
| `reconcile_in_flight` | Envio em andamento ou resultado incerto; consultar o Google antes de repetir |
| `review_changed_file` | Arquivo alterado depois do registro local |
| `associate_identical_content` | Conteúdo idêntico a uma fonte já registrada no mesmo notebook; associar os recursos |
| `duplicate_local_content` | Dois recursos candidatos possuem os mesmos bytes; preparar apenas o primeiro envio |
| `associate_notebook` | Falta o ID do notebook de destino |
| `missing_file` / `unsupported_format` | Arquivo ausente ou extensão fora do escopo |

Um nome igual nunca basta para declarar que o conteúdo está sincronizado. Um recibo exige ID da fonte, ID do notebook, hash dos bytes enviados e confirmação de processamento. Os recibos dos pilotos foram preenchidos somente após observar esses resultados no navegador.

## Formato mínimo do inventário

```json
{
  "course_id": "example-course",
  "google_notebook_id": "example-notebook",
  "resources": [
    {
      "resource_id": "example-resource",
      "title": "Aula de exemplo",
      "local_path": "data/materials/example.pdf"
    }
  ]
}
```

Depois do envio confirmado, o conector registra `google_source_id`, `uploaded_notebook_id`, `uploaded_sha256` e `google_upload_status` igual a `processed` ou `processed-and-cited`. A prévia calcula o hash do arquivo atual, em vez de confiar no nome.

## Validação e limites

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Depois de instalar as dependências opcionais do coletor, a suíte completa tem 12 testes. Os testes do planejador cobrem repetição da prévia, conteúdo duplicado, alteração de arquivo, recibo de outro notebook, resultado de upload incerto, arquivo ausente, IDs repetidos, caminhos longos do Windows e tentativa de sair da pasta do projeto. Os demais verificam a proteção do formulário local de autorização. Todos usam dados sintéticos.

Sobre os dois inventários reais, o planejador reconheceu os oito novos envios registrados e não os colocou novamente na fila. Fontes antigas sem hash permanecem para revisão; recursos fora das amostras ficam aguardando download.

Essa é uma prévia **offline**. Ela não detecta uma fonte que alguém apagou no Google depois de gerar o recibo. Antes de executar qualquer fila, o futuro conector deverá ler o estado remoto, confirmar a conta e o notebook e reconciliar exclusões e tentativas pendentes. O próximo trabalho é conectar essa prévia à coleta e ao envio repetíveis.
