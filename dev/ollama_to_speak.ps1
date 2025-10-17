Param(
  [string]$Model = "gemma3:1b",
  [string]$Prompt = "Please write one friendly sentence, under 20 words, to read aloud.",
  [string]$OutFile = "tmp_ollama_to_speak.txt"
)

$body = @{ model = $Model; messages = @(@{ role = 'user'; content = $Prompt }); stream = $false } | ConvertTo-Json

try {
    $r = Invoke-RestMethod -Uri 'http://localhost:11434/api/chat' -Method Post -ContentType 'application/json' -Body $body
    $text = $r.message.content
    if ([string]::IsNullOrWhiteSpace($text)) { $text = 'Hello there, wishing you a wonderful day.' }
    $text | Out-File -FilePath $OutFile -Encoding UTF8 -Force
} catch {
    'Hello there, wishing you a wonderful day.' | Out-File -FilePath $OutFile -Encoding UTF8 -Force
}
