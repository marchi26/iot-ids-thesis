param([string]$RepositoryRoot = (Split-Path -Parent $PSScriptRoot), [string]$SignaturePath = (Join-Path $env:USERPROFILE 'Documents\Firma.png'))
$ErrorActionPreference = 'Stop'
$docxPath = Join-Path $RepositoryRoot 'thesis\final_thesis.docx'
$pdfPath = Join-Path $RepositoryRoot 'thesis\final_thesis_revisionata.pdf'
$abstractDocx = Join-Path $RepositoryRoot 'thesis\abstract_tesi.docx'
$abstractPdf = Join-Path $RepositoryRoot 'thesis\abstract_tesi.pdf'
$submissionDir = Join-Path $RepositoryRoot 'thesis\submission'
$signedDocx = Join-Path $submissionDir 'tesi_deposito_firmata_finale.docx'
$signedPdf = Join-Path $submissionDir 'tesi_deposito_firmata_finale.pdf'
$wdAlignCenter=1; $wdAlignJustify=3; $wdCollapseEnd=0; $wdSectionBreakNextPage=2
$wdPageLowerRoman=2; $wdPageArabic=0; $wdFieldEmpty=-1; $wdFormatDocx=16; $wdExportPdf=17
$word=$null; $doc=$null; $summary=$null; $signed=$null
try {
  $word=New-Object -ComObject Word.Application
  $word.Visible=$false; $word.DisplayAlerts=0
  $doc=$word.Documents.Open($docxPath)
  foreach($existingParagraph in @($doc.Paragraphs)){
    if($existingParagraph.Range.Text.Trim([char]13,[char]7,' ') -eq 'AUTORIZZAZIONE ALLA CONSULTAZIONE DELLA TESI DI LAUREA'){
      throw 'Documento già formattato: rigenerare final_thesis.docx con build_final_docx.py prima di rieseguire questo script.'
    }
  }
  $doc.Repaginate()
  $page2=$doc.GoTo(1,1,2)
  $authorization=@"
AUTORIZZAZIONE ALLA CONSULTAZIONE DELLA TESI DI LAUREA

Il sottoscritto Samuele Marchitelli, matricola n. 001814763,
autore della tesi dal titolo:

“Sicurezza nei sistemi Internet of Things: architetture, vulnerabilità e strategie di mitigazione”

☒ AUTORIZZA
☐ NON AUTORIZZA

la consultazione della tesi, fatto divieto di riprodurne parzialmente o integralmente il contenuto senza corretta attribuzione.

Dichiara inoltre di:

☒ AUTORIZZARE
☐ NON AUTORIZZARE

l’Università Telematica eCampus, nei limiti previsti dalla normativa vigente, al trattamento, alla comunicazione, alla diffusione e alla pubblicazione dei dati personali per le finalità istituzionali connesse alla tesi di laurea.

Data: 26/08/2026

Firma: ______________________________

"@
  $page2.InsertBefore($authorization)
  foreach($p in @($doc.Paragraphs)){
    $t=$p.Range.Text.Trim([char]13,[char]7,' ')
    if($t -eq 'AUTORIZZAZIONE ALLA CONSULTAZIONE DELLA TESI DI LAUREA'){
      $authTitle=$p
      break
    }
  }  $inAuthorization=$false
  foreach($p in @($doc.Paragraphs)){
    $t=$p.Range.Text.Trim([char]13,[char]7,' ')
    if($t -eq 'AUTORIZZAZIONE ALLA CONSULTAZIONE DELLA TESI DI LAUREA'){$inAuthorization=$true}
    if($inAuthorization){
      $p.Range.Font.Name='Times New Roman'; $p.Range.Font.Size=11
      $p.Range.ParagraphFormat.LineSpacingRule=0; $p.Range.ParagraphFormat.SpaceAfter=$word.PointsToPixels(0)
      if($t -eq 'AUTORIZZAZIONE ALLA CONSULTAZIONE DELLA TESI DI LAUREA'){$p.Range.Bold=1;$p.Range.Font.Size=14;$p.Range.ParagraphFormat.Alignment=$wdAlignCenter}
      if($t -like 'Firma:*'){$inAuthorization=$false}
    }
  }
  foreach($section in $doc.Sections){
    $section.PageSetup.TopMargin=$word.CentimetersToPoints(2.5)
    $section.PageSetup.BottomMargin=$word.CentimetersToPoints(2.5)
    $section.PageSetup.LeftMargin=$word.CentimetersToPoints(2.5)
    $section.PageSetup.RightMargin=$word.CentimetersToPoints(2.5)
    $section.PageSetup.Gutter=$word.CentimetersToPoints(1.0)
  }
  $normal=$doc.Styles.Item(-1)
  $normal.Font.Name='Times New Roman'; $normal.Font.Size=12
  $normal.ParagraphFormat.Alignment=$wdAlignJustify
  $normal.ParagraphFormat.LineSpacingRule=1
  $normal.ParagraphFormat.WidowControl=-1

  foreach($styleName in @('FigureCaption','TableCaption')){
    try{$style=$doc.Styles.Item($styleName)}catch{$style=$doc.Styles.Add($styleName,1)}
    $style.Font.Name='Times New Roman'; $style.Font.Size=10; $style.Font.Italic=$true
    $style.ParagraphFormat.Alignment=$wdAlignCenter
  }
  foreach($p in @($doc.Paragraphs)){
    $t=$p.Range.Text.Trim([char]13,[char]7,' ')
    if($t -match '^Figura\s+\d+\s+-'){
      $p.Range.Style=$doc.Styles.Item('FigureCaption')
      $r=$p.Range.Duplicate; $r.End=$r.End-1; $r.Collapse($wdCollapseEnd)
      [void]$doc.Fields.Add($r,$wdFieldEmpty,('TC "'+$t.Replace('"','')+'" \f F'),$false)
    }
    elseif($t -match '^Tabella\s+\d+\s+-'){
      $p.Range.Style=$doc.Styles.Item('TableCaption')
      $r=$p.Range.Duplicate; $r.End=$r.End-1; $r.Collapse($wdCollapseEnd)
      [void]$doc.Fields.Add($r,$wdFieldEmpty,('TC "'+$t.Replace('"','')+'" \f T'),$false)
    }
  }

  $indexPara=$null; $chapterPara=$null
  foreach($p in @($doc.Paragraphs)){
    $t=$p.Range.Text.Trim([char]13,[char]7,' ')
    if(-not $indexPara -and $t -eq 'Indice'){$indexPara=$p}
    if($t -eq 'Capitolo 1 - Introduzione'){$chapterPara=$p}
  }
  if(-not $indexPara -or -not $chapterPara){throw 'Indice o Capitolo 1 non trovato'}
  $tocStart=$indexPara.Range.End
  $doc.Range($tocStart,$chapterPara.Range.Start).Delete()

  foreach($p in @($doc.Paragraphs)){
    $t=$p.Range.Text.Trim([char]13,[char]7,' ')
    if($t -eq 'Abstract'){$p.Range.Style=$doc.Styles.Item(-2);$p.Range.ParagraphFormat.KeepWithNext=-1;$p.Range.ParagraphFormat.KeepTogether=-1}
    elseif($t -eq 'Bibliografia'){$p.Range.Style=$doc.Styles.Item(-2);$p.Range.ParagraphFormat.PageBreakBefore=-1;$p.Range.ParagraphFormat.KeepWithNext=-1}
    elseif($t -match '^Capitolo\s+\d+'){$p.Range.Style=$doc.Styles.Item(-2);$p.Range.ParagraphFormat.KeepWithNext=-1;$p.Range.ParagraphFormat.KeepTogether=-1;if($t -notlike 'Capitolo 1*'){$p.Range.ParagraphFormat.PageBreakBefore=-1}}
    elseif($t -match '^\d+\.\d+\s+'){$p.Range.Style=$doc.Styles.Item(-3);$p.Range.ParagraphFormat.KeepWithNext=-1;$p.Range.ParagraphFormat.KeepTogether=-1}
  }
  $tocRange=$doc.Range($tocStart,$tocStart)
  [void]$doc.TablesOfContents.Add($tocRange,$true,1,2,$false,'',$true,$true,'',$true,$true,$true)
  $insert=$doc.Range($doc.TablesOfContents.Item(1).Range.End,$doc.TablesOfContents.Item(1).Range.End)
  $insert.InsertAfter("`r`fElenco delle figure`rFIGURE_FIELD`r`fElenco delle tabelle`rTABLE_FIELD`r`f")

  foreach($p in @($doc.Paragraphs)){
    $t=$p.Range.Text.Trim([char]13,[char]7,' ',[char]12)
    if($t -in @('Elenco delle figure','Elenco delle tabelle')){$p.Range.Style=$doc.Styles.Item(-2)}
  }
  foreach($spec in @(@('FIGURE_FIELD','TOC \h \z \f F'),@('TABLE_FIELD','TOC \h \z \f T'))){
    $findRange=$doc.Content.Duplicate
    $findRange.Find.Text=$spec[0]
    if(-not $findRange.Find.Execute()){throw "Segnaposto $($spec[0]) non trovato"}
    $findRange.Text=''
    [void]$doc.Fields.Add($findRange,$wdFieldEmpty,$spec[1],$true)
    $findRange.Paragraphs.Item(1).Range.Style=$doc.Styles.Item(-1)
  }

  foreach($p in @($doc.Paragraphs)){
    $p.Range.ParagraphFormat.WidowControl=-1
    if($p.Range.InlineShapes.Count -gt 0){$p.Range.ParagraphFormat.KeepWithNext=-1;$p.Range.ParagraphFormat.KeepTogether=-1}
    $t=$p.Range.Text.Trim([char]13,[char]7,' ')
    if($t -match '^(Figura|Tabella)\s+\d+\s+-'){$p.Range.ParagraphFormat.KeepTogether=-1}
    if($t -match '^Tabella\s+\d+\s+-'){$p.Range.ParagraphFormat.KeepWithNext=-1}
  }
  foreach($table in @($doc.Tables)){
    $table.AutoFitBehavior(2)
    $table.Range.Font.Name='Times New Roman'; $table.Range.Font.Size=9
    $table.Range.ParagraphFormat.LineSpacingRule=0; $table.Range.ParagraphFormat.SpaceBefore=0; $table.Range.ParagraphFormat.SpaceAfter=0
    $table.Rows.AllowBreakAcrossPages=0
    for($rowIndex=1;$rowIndex -lt $table.Rows.Count;$rowIndex++){
      $table.Rows.Item($rowIndex).Range.ParagraphFormat.KeepWithNext=-1
      $table.Rows.Item($rowIndex).Range.ParagraphFormat.KeepTogether=-1
    }
    $table.Rows.Item($table.Rows.Count).Range.ParagraphFormat.KeepTogether=-1
  }
  $bodySearch=$doc.Content.Duplicate
  $bodySearch.Start=$doc.TablesOfContents.Item(3).Range.End
  $bodySearch.Find.Text='Capitolo 1 - Introduzione'
  $bodySearch.Find.MatchCase=$true; $bodySearch.Find.MatchWholeWord=$true
  if(-not $bodySearch.Find.Execute()){throw 'Inizio del Capitolo 1 non trovato'}
  $doc.Range($bodySearch.Start,$bodySearch.Start).InsertBreak($wdSectionBreakNextPage)
  if($doc.Sections.Count -lt 2){throw 'Creazione delle sezioni non riuscita'}
  $sec1=$doc.Sections.Item(1); $sec2=$doc.Sections.Item(2)
  $sec1.PageSetup.DifferentFirstPageHeaderFooter=$true
  $sec1.Footers.Item(2).Range.Text=''
  $f1=$sec1.Footers.Item(1); $f1.Range.ParagraphFormat.Alignment=$wdAlignCenter
  [void]$f1.PageNumbers.Add($wdAlignCenter,$false); $f1.PageNumbers.NumberStyle=$wdPageLowerRoman
  $f1.PageNumbers.RestartNumberingAtSection=$true; $f1.PageNumbers.StartingNumber=1
  $f2=$sec2.Footers.Item(1); $f2.LinkToPrevious=$false; $f2.Range.ParagraphFormat.Alignment=$wdAlignCenter
  [void]$f2.PageNumbers.Add($wdAlignCenter,$true); $f2.PageNumbers.NumberStyle=$wdPageArabic
  $f2.PageNumbers.RestartNumberingAtSection=$true; $f2.PageNumbers.StartingNumber=1

  $doc.Repaginate()
  for($tableIndex=1;$tableIndex -le $doc.Tables.Count;$tableIndex++){
    $table=$doc.Tables.Item($tableIndex)
    $startRange=$table.Range.Duplicate; $startRange.Collapse(1)
    $endRange=$table.Range.Duplicate; $endRange.Collapse(0)
    if($startRange.Information(3) -ne $endRange.Information(3)){
      foreach($p in @($doc.Paragraphs)){
        $t=$p.Range.Text.Trim([char]13,[char]7,' ')
        if($t -match "^Tabella\s+$tableIndex\s+-"){
          $p.Range.ParagraphFormat.PageBreakBefore=-1
          $p.Range.ParagraphFormat.KeepWithNext=-1
          break
        }
      }
    }
  }
  $doc.Repaginate()
  $doc.Fields.Update() | Out-Null
  foreach($toc in @($doc.TablesOfContents)){$toc.Update()}
  $doc.Save()
  $pdfTemp=Join-Path $RepositoryRoot 'thesis\final_thesis.new.pdf'
  Remove-Item -LiteralPath $pdfTemp -Force -ErrorAction SilentlyContinue
  $doc.ExportAsFixedFormat($pdfTemp,$wdExportPdf)
  Remove-Item -LiteralPath $pdfPath -Force -ErrorAction SilentlyContinue
  Move-Item -LiteralPath $pdfTemp -Destination $pdfPath -Force

  if(-not (Test-Path -LiteralPath $SignaturePath)){throw "File firma non trovato: $SignaturePath"}
  [IO.Directory]::CreateDirectory($submissionDir) | Out-Null
  Copy-Item -LiteralPath $docxPath -Destination $signedDocx -Force
  $signed=$word.Documents.Open($signedDocx)
  $signatureRange=$signed.Content.Duplicate
  $signatureRange.Find.Text='______________________________'
  if(-not $signatureRange.Find.Execute()){throw 'Riga della firma non trovata'}
  $signatureRange.Text=''
  [void]$signed.InlineShapes.AddPicture($SignaturePath,$false,$true,$signatureRange)
  $shape=$signed.InlineShapes.Item($signed.InlineShapes.Count)
  $shape.LockAspectRatio=-1; $shape.Width=$word.CentimetersToPoints(5.5)
  $signed.Save()
  $signed.ExportAsFixedFormat($signedPdf,$wdExportPdf)
  $signed.Close($true); $signed=$null
  $md=[IO.File]::ReadAllText((Join-Path $RepositoryRoot 'thesis\final_thesis.md'))
  $abstractMatch=[regex]::Match($md,'(?s)## Abstract\s+(.*?)\s+## Capitolo 1')
  $bibMatch=[regex]::Match($md,'(?s)## Bibliografia\s+(.*)$')
  if(-not $abstractMatch.Success -or -not $bibMatch.Success){throw 'Abstract o bibliografia non trovati nella sorgente Markdown'}
  $abstractText=($abstractMatch.Groups[1].Value -replace '`','').Trim()
  $bibText=("Bibliografia`r`r" + ($bibMatch.Groups[1].Value -replace '`','').Trim())
  if($abstractText.Length -gt 4000){throw "Il riassunto supera 4000 caratteri: $($abstractText.Length)"}

  $summary=$word.Documents.Add()
  $summary.PageSetup.TopMargin=$word.CentimetersToPoints(2.5); $summary.PageSetup.BottomMargin=$word.CentimetersToPoints(2.5)
  $summary.PageSetup.LeftMargin=$word.CentimetersToPoints(2.5); $summary.PageSetup.RightMargin=$word.CentimetersToPoints(2.5)
  $summary.Styles.Item(-1).Font.Name='Times New Roman'; $summary.Styles.Item(-1).Font.Size=12
  $summary.Styles.Item(-1).ParagraphFormat.Alignment=$wdAlignJustify; $summary.Styles.Item(-1).ParagraphFormat.LineSpacingRule=1
  $content="UNIVERSITÀ TELEMATICA e-Campus`rCorso di Laurea in INGEGNERIA INFORMATICA E DELL'AUTOMAZIONE (DM 1648/23)`r`rSicurezza nei sistemi Internet of Things: architetture, vulnerabilità e strategie di mitigazione`r`rStudente: Samuele Marchitelli`rMatricola: 001814763`rRelatore: Prof. Oleksandr Kuznetsov`rAnno Accademico 2025/2026`r`fINDICE DELL'ELABORATO`r1. Introduzione`r2. Stato dell'arte`r3. Metodologia`r4. Risultati sperimentali`r5. Discussione e strategie di mitigazione`r6. Conclusioni`rBibliografia`r`fRIASSUNTO`r$abstractText`r`f$bibText"
  $summary.Content.Text=$content
  foreach($p in @($summary.Paragraphs)){
    $t=$p.Range.Text.Trim([char]13,[char]7,' ')
    if($t -in @('UNIVERSITÀ TELEMATICA e-Campus','INDICE DELL''ELABORATO','RIASSUNTO','Bibliografia')){$p.Range.Bold=1;$p.Range.ParagraphFormat.Alignment=$wdAlignCenter}
  }
  $summary.SaveAs2($abstractDocx,$wdFormatDocx)
  $summary.ExportAsFixedFormat($abstractPdf,$wdExportPdf)
  Write-Output "Documento finale: $docxPath"
  Write-Output "PDF finale: $pdfPath"
  Write-Output "Tesi firmata: $signedDocx"
  Write-Output "PDF firmato: $signedPdf"
  Write-Output "Riassunto: $abstractDocx"
  Write-Output "PDF riassunto: $abstractPdf"
  Write-Output "Caratteri riassunto: $($abstractText.Length)"
}
finally{
  if($signed){$signed.Close($false)}
  if($summary){$summary.Close($false)}
  if($doc){$doc.Close($true)}
  if($word){$word.Quit()}
}