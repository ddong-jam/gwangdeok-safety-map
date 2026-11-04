param([string]$dir, [string]$out)
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime]
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Await($op, [Type]$t) { $task = $asTask.MakeGenericMethod($t).Invoke($null, @($op)); $task.Wait(-1) | Out-Null; $task.Result }

$eng = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
$lines = New-Object System.Collections.Generic.List[string]
Get-ChildItem $dir -Filter *.png | ForEach-Object {
  $f = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($_.FullName)) ([Windows.Storage.StorageFile])
  $s = Await ($f.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
  $d = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($s)) ([Windows.Graphics.Imaging.BitmapDecoder])
  $b = Await ($d.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
  $r = Await ($eng.RecognizeAsync($b)) ([Windows.Media.Ocr.OcrResult])
  foreach ($l in $r.Lines) {
    $x0=1e9;$y0=1e9;$x1=0;$y1=0
    foreach ($w in $l.Words) { $q=$w.BoundingRect; $x0=[Math]::Min($x0,$q.X);$y0=[Math]::Min($y0,$q.Y);$x1=[Math]::Max($x1,$q.X+$q.Width);$y1=[Math]::Max($y1,$q.Y+$q.Height) }
    $lines.Add("$($_.BaseName)`t$([int]$x0)`t$([int]$y0)`t$([int]$x1)`t$([int]$y1)`t$($l.Text)")
  }
  $s.Dispose()
}
[IO.File]::WriteAllLines($out, $lines, [Text.Encoding]::UTF8)
