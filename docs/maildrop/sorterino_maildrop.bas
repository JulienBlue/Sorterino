VERSION 1.0 CLASS
BEGIN
  MultiUse = -1  'True
END
Attribute VB_Name = "ThisOutlookSession"
Attribute VB_GlobalNameSpace = False
Attribute VB_Creatable = False
Attribute VB_PredeclaredId = True
Attribute VB_Exposed = True

Private Sub Application_Startup()
    ' Produktionsbetrieb – keine UI-Ausgaben
End Sub


Private Sub Application_NewMailEx(ByVal EntryIDCollection As String)

    On Error GoTo ErrorHandler

    Dim arr() As String
    Dim i As Integer
    
    arr = Split(EntryIDCollection, ",")
    
    For i = 0 To UBound(arr)
        
        Dim mail As Object
        Set mail = Application.Session.GetItemFromID(arr(i))
        
        If TypeOf mail Is Outlook.MailItem Then
            
            If mail.Attachments.Count > 0 Then
                
                Dim savePath As String
                savePath = "C:\\Users\\JulienBlueHirte\\OneDrive - Hades IT GmbH\\Tanja\\Hades IT GmbH - Autotest\\.sorterino_runtime\\incoming\\"
                
                ' Falls Ordner nicht existiert → überspringen
                If Dir(savePath, vbDirectory) = "" Then GoTo NextMail
                
                Dim j As Integer
                For j = 1 To mail.Attachments.Count
                    
                    Dim attachment As Outlook.Attachment
                    Set attachment = mail.Attachments(j)
                    
                    Dim fileName As String
                    fileName = attachment.FileName
                    
                    If IsSupportedExtension(fileName) Then
                        
                        ' Eindeutiger Zeitstempel + Index
                        Dim timestamp As String
                        timestamp = Format(Now, "yyyymmdd_hhnnss_")
                        
                        Dim uniqueName As String
                        uniqueName = timestamp & j & "_" & fileName
                        
                        attachment.SaveAsFile savePath & uniqueName
                        
                    End If
                    
                Next j
                
            End If
            
        End If
        
NextMail:
    Next i

    Exit Sub

ErrorHandler:
    Resume Next

End Sub


Private Function IsSupportedExtension(fileName As String) As Boolean
    
    Dim ext As String
    ext = LCase(Mid(fileName, InStrRev(fileName, ".")))
    
    Select Case ext
        Case ".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".bmp"
            IsSupportedExtension = True
        Case Else
            IsSupportedExtension = False
    End Select

End Function