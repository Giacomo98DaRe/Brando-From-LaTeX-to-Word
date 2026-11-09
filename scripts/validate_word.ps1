<#
Optional Windows-only validation using an installed Microsoft Word instance.
The conversion application itself has no dependency on Word or COM automation.
The manifest contains a samples array with name, docx and expected_text fields.
#>
param(
    [Parameter(Mandatory = $true)][string]$ManifestPath,
    [Parameter(Mandatory = $true)][string]$OutputDirectory
)

$ErrorActionPreference = 'Stop'
$manifestFile = Get-Item -LiteralPath $ManifestPath
$manifest = Get-Content -LiteralPath $manifestFile.FullName -Raw | ConvertFrom-Json
if (-not $manifest.samples -or @($manifest.samples).Count -eq 0) {
    throw 'The validation manifest must contain at least one sample.'
}
$outputRoot = [IO.Path]::GetFullPath($OutputDirectory)
if (Test-Path -LiteralPath $outputRoot) {
    throw 'Choose a fresh validation output directory.'
}
[void](New-Item -ItemType Directory -Path $outputRoot)
$records = [Collections.Generic.List[object]]::new()
$wordInstance = $null

try {
    $wordInstance = New-Object -ComObject Word.Application
    if ($wordInstance.Documents.Count -ne 0) {
        $wordInstance = $null
        throw 'The automation instance already contains documents. Validation stopped.'
    }
    $wordInstance.Visible = $false
    $wordInstance.DisplayAlerts = 0
    $wordInstance.AutomationSecurity = 3
    $sampleNumber = 0

    foreach ($sample in $manifest.samples) {
        $sampleNumber += 1
        $document = $null
        $safeName = [regex]::Replace([string]$sample.name, '[^A-Za-z0-9_-]', '_')
        $sampleFolder = Join-Path $outputRoot ('{0:D2}-{1}' -f $sampleNumber, $safeName)
        [void](New-Item -ItemType Directory -Path $sampleFolder)
        $record = [ordered]@{ sample = [string]$sample.name }

        try {
            $sourcePath = [string]$sample.docx
            if (-not [IO.Path]::IsPathRooted($sourcePath)) {
                $sourcePath = Join-Path $manifestFile.DirectoryName $sourcePath
            }
            $source = Get-Item -LiteralPath $sourcePath
            if ($source.Extension -ne '.docx') {
                throw 'Validation accepts DOCX inputs only.'
            }
            $beforeHash = (Get-FileHash -LiteralPath $source.FullName -Algorithm SHA256).Hash
            $document = $wordInstance.Documents.Open($source.FullName, $false, $true, $false)
            $document.Repaginate()
            $wordText = [regex]::Replace($document.Content.Text, '\s+', ' ')
            $presence = [ordered]@{}
            foreach ($expected in $sample.expected_text) {
                $presence[[string]$expected] = $wordText.Contains([string]$expected)
            }
            $pdfFile = Join-Path $sampleFolder 'word-render.pdf'
            $document.ExportAsFixedFormat($pdfFile, 17)
            $record['word_version'] = $wordInstance.Version
            $record['word_build'] = $wordInstance.Build
            $record['pages'] = $document.ComputeStatistics(2)
            $record['tables'] = $document.Tables.Count
            $record['equations'] = $document.OMaths.Count
            $record['comments'] = $document.Comments.Count
            $record['footnotes'] = $document.Footnotes.Count
            $record['inline_shapes'] = $document.InlineShapes.Count
            $record['text_presence'] = $presence
            $record['source_sha256'] = $beforeHash
            $record['pdf'] = [IO.Path]::GetFileName($sampleFolder) + '/word-render.pdf'
        }
        catch {
            $record['error'] = $_.Exception.Message
        }
        finally {
            if ($document) {
                $document.Close(0)
                [void][Runtime.InteropServices.Marshal]::ReleaseComObject($document)
            }
        }

        if ($record.Contains('source_sha256')) {
            $afterHash = (Get-FileHash -LiteralPath $source.FullName -Algorithm SHA256).Hash
            $record['source_unchanged'] = $record['source_sha256'] -eq $afterHash
        }
        $records.Add($record)
        ConvertTo-Json -InputObject ($records.ToArray()) -Depth 8 |
            Set-Content -LiteralPath (Join-Path $outputRoot 'word-results.json') -Encoding UTF8
        Write-Output ($record | ConvertTo-Json -Depth 8 -Compress)
    }
}
finally {
    if ($wordInstance) {
        $wordInstance.Quit(0)
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($wordInstance)
    }
}

if ($records | Where-Object { $_.Contains('error') -or -not $_.source_unchanged }) {
    exit 1
}
foreach ($record in $records) {
    if ($record.text_presence.Values -contains $false) {
        exit 1
    }
}
