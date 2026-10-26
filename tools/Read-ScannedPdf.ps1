param([Parameter(Mandatory=$true)][string]$InputPdf, [Parameter(Mandatory=$true)][string]$OutputText)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null=[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null=[Windows.Data.Pdf.PdfDocument,Windows.Data.Pdf,ContentType=WindowsRuntime]
$null=[Windows.Storage.Streams.InMemoryRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
$null=[Windows.Graphics.Imaging.BitmapDecoder,Windows.Graphics.Imaging,ContentType=WindowsRuntime]
$null=[Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
$asyncMethod=[System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetGenericArguments().Count -eq 1 -and $_.GetParameters().Count -eq 1 } | Select-Object -First 1
function Await-Result($Operation,[Type]$Type) {
    $task=$asyncMethod.MakeGenericMethod($Type).Invoke($null,@($Operation))
    $task.GetAwaiter().GetResult()
}
function Await-Action($Operation) {
    $method=[System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and -not $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.FullName -eq 'Windows.Foundation.IAsyncAction' } | Select-Object -First 1
    $task=$method.Invoke($null,@($Operation))
    $null=$task.GetAwaiter().GetResult()
}
$file=Await-Result ([Windows.Storage.StorageFile]::GetFileFromPathAsync((Resolve-Path -LiteralPath $InputPdf).Path)) ([Windows.Storage.StorageFile])
$pdf=Await-Result ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($file)) ([Windows.Data.Pdf.PdfDocument])
if ($pdf.PageCount -gt 80) { throw 'PDF excede o limite de leitura local.' }
$engine=[Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if (-not $engine) { throw 'Reconhecimento de texto indisponivel neste Windows.' }
$text=New-Object System.Text.StringBuilder
[void]$text.AppendLine('Texto reconhecido automaticamente. Consulte o PDF original para imagens, diagramas e conferencias.')
for ($index=0; $index -lt $pdf.PageCount; $index++) {
    $page=$pdf.GetPage($index)
    $stream=New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
    $options=New-Object Windows.Data.Pdf.PdfPageRenderOptions
    $options.DestinationWidth=[uint32][Math]::Min(1800,[Math]::Floor(2400*$page.Size.Width/$page.Size.Height))
    try {
        Await-Action ($page.RenderToStreamAsync($stream,$options))
        $decoder=Await-Result ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap=Await-Result ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        try {
            $result=Await-Result ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
            [void]$text.AppendLine(('--- Pagina ' + ($index+1) + ' ---'))
            [void]$text.AppendLine($result.Text)
            [void]$text.AppendLine('')
        } finally { $bitmap.Dispose() }
    } finally { $page.Dispose(); $stream.Dispose() }
}
if ($text.Length -lt 350) { throw 'Nao foi possivel reconhecer texto suficiente.' }
[System.IO.File]::WriteAllText($OutputText,$text.ToString(),(New-Object System.Text.UTF8Encoding($false)))
@{ pages=$pdf.PageCount; characters=$text.Length; language=$engine.RecognizerLanguage.LanguageTag } | ConvertTo-Json -Compress
