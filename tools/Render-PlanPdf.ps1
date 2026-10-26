param([Parameter(Mandatory=$true)][string]$InputPdf, [Parameter(Mandatory=$true)][string]$OutputImage)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null=[Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null=[Windows.Data.Pdf.PdfDocument,Windows.Data.Pdf,ContentType=WindowsRuntime]
$null=[Windows.Storage.Streams.InMemoryRandomAccessStream,Windows.Storage.Streams,ContentType=WindowsRuntime]
$asyncMethod=[System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetGenericArguments().Count -eq 1 -and $_.GetParameters().Count -eq 1 } | Select-Object -First 1
function Await-Result($Operation,[Type]$Type) {
    $task=$asyncMethod.MakeGenericMethod($Type).Invoke($null,@($Operation))
    $task.GetAwaiter().GetResult()
}
$file=Await-Result ([Windows.Storage.StorageFile]::GetFileFromPathAsync((Resolve-Path -LiteralPath $InputPdf).Path)) ([Windows.Storage.StorageFile])
$pdf=Await-Result ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($file)) ([Windows.Data.Pdf.PdfDocument])
# Uma imagem representa somente uma página. Nunca descartar páginas seguintes.
if ($pdf.PageCount -ne 1) { throw 'A alternativa em imagem requer PDF de uma pagina.' }
$page=$pdf.GetPage(0)
$stream=New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
try {
    $options=New-Object Windows.Data.Pdf.PdfPageRenderOptions
    $options.DestinationWidth=[uint32][Math]::Min(4000,[Math]::Floor(4000*$page.Size.Width/$page.Size.Height))
    $method=[System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and -not $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.FullName -eq 'Windows.Foundation.IAsyncAction' } | Select-Object -First 1
    $task=$method.Invoke($null,@($page.RenderToStreamAsync($stream,$options)))
    $null=$task.GetAwaiter().GetResult()
    $stream.Seek(0)
    $reader=[System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($stream)
    $target=[System.IO.File]::Create($OutputImage)
    try { $reader.CopyTo($target) } finally { $target.Dispose(); $reader.Dispose() }
} finally { $page.Dispose(); $stream.Dispose() }
