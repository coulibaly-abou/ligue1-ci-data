# Synthèse vocale hors ligne avec les voix françaises de Windows (Paul, Julie, Hortense).
#   powershell -NoProfile -ExecutionPolicy Bypass -File tts_windows.ps1 -Texte "..." -Sortie voix.wav
param([string]$Texte, [string]$Sortie, [string]$Voix = "Paul", [double]$Vitesse = 1.0)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.SpeechSynthesis.SpeechSynthesizer, Windows.Media.SpeechSynthesis, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.DataReader, Windows.Storage.Streams, ContentType = WindowsRuntime]
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
function Attendre($op, [Type]$t) {
    $task = $asTask.MakeGenericMethod($t).Invoke($null, @($op)); $task.Wait(-1) | Out-Null; $task.Result
}
$s = New-Object Windows.Media.SpeechSynthesis.SpeechSynthesizer
$voixTrouvee = [Windows.Media.SpeechSynthesis.SpeechSynthesizer]::AllVoices |
    Where-Object { $_.DisplayName -like "*$Voix*" -and $_.Language -like "fr*" } | Select-Object -First 1
if ($null -eq $voixTrouvee) { throw "Voix française '$Voix' introuvable" }
$s.Voice = $voixTrouvee
$s.Options.SpeakingRate = $Vitesse
$flux = Attendre ($s.SynthesizeTextToStreamAsync($Texte)) ([Windows.Media.SpeechSynthesis.SpeechSynthesisStream])
$lecteur = New-Object Windows.Storage.Streams.DataReader($flux.GetInputStreamAt(0))
$n = [uint32]$flux.Size
Attendre ($lecteur.LoadAsync($n)) ([uint32]) | Out-Null
$octets = New-Object byte[] $n
$lecteur.ReadBytes($octets)
[IO.File]::WriteAllBytes($Sortie, $octets)
