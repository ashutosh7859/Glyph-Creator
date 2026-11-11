;;; Extract TEXT and MTEXT properties to a CSV-formatted .txt report.
;;; Load with APPLOAD, then run GLYPHREPORT.

(defun gc:field (entity code default)
  (if (assoc code entity)
    (cdr (assoc code entity))
    default
  )
)

(defun gc:number (value)
  (if (numberp value)
    (rtos value 2 6)
    ""
  )
)

(defun gc:csv (value / text result index character)
  (setq text (if value value ""))
  (setq result "\"")
  (setq index 1)
  (while (<= index (strlen text))
    (setq character (substr text index 1))
    (cond
      ((= character "\"") (setq result (strcat result "\"\"")))
      ((= (ascii character) 10) (setq result (strcat result "\\n")))
      ((= (ascii character) 13) (setq result (strcat result "\\r")))
      (T (setq result (strcat result character)))
    )
    (setq index (1+ index))
  )
  (strcat result "\"")
)

(defun gc:text-content (entity / content pair)
  (setq content "")
  (foreach pair entity
    (if (or (= (car pair) 1) (= (car pair) 3))
      (setq content (strcat content (cdr pair)))
    )
  )
  content
)

(defun gc:write-entity (file entity / kind style-name style font bigfont text-height width-factor oblique rotation point align-point hjust vjust box-width attachment line-style line-factor)
  (setq kind (gc:field entity 0 ""))
  (setq style-name (gc:field entity 7 ""))
  (setq style (tblsearch "STYLE" style-name))
  (setq font (if style (gc:field style 3 "") ""))
  (setq bigfont (if style (gc:field style 4 "") ""))
  (setq text-height (gc:field entity 40 0.0))
  (if (and (= kind "TEXT") (= text-height 0.0))
    (setq text-height (if style (gc:field style 40 0.0) 0.0))
  )
  (setq width-factor
    (if (= kind "TEXT")
      (gc:field entity 41 (if style (gc:field style 41 1.0) 1.0))
      ""
    )
  )
  (setq oblique
    (gc:field entity 51 (if style (gc:field style 50 0.0) 0.0))
  )
  (setq rotation (gc:field entity 50 0.0))
  (setq point (gc:field entity 10 '(0.0 0.0 0.0)))
  (setq align-point (gc:field entity 11 point))
  (setq hjust (if (= kind "TEXT") (gc:field entity 72 "") ""))
  (setq vjust (if (= kind "TEXT") (gc:field entity 73 "") ""))
  (setq box-width (if (= kind "MTEXT") (gc:field entity 41 "") ""))
  (setq attachment (if (= kind "MTEXT") (gc:field entity 71 "") ""))
  (setq line-style (if (= kind "MTEXT") (gc:field entity 73 "") ""))
  (setq line-factor (if (= kind "MTEXT") (gc:field entity 44 "") ""))
  (write-line
    (strcat
      (gc:csv (gc:field entity 5 ""))
      "," (gc:csv kind)
      "," (gc:csv (gc:field entity 8 ""))
      "," (gc:csv (gc:text-content entity))
      "," (gc:csv style-name)
      "," (gc:csv font)
      "," (gc:csv bigfont)
      "," (gc:csv (gc:number text-height))
      "," (gc:csv (gc:number width-factor))
      "," (gc:csv (gc:number (* oblique (/ 180.0 pi))))
      "," (gc:csv (gc:number (* rotation (/ 180.0 pi))))
      "," (gc:csv (gc:number (nth 0 point)))
      "," (gc:csv (gc:number (nth 1 point)))
      "," (gc:csv (gc:number (nth 2 point)))
      "," (gc:csv (gc:number (nth 0 align-point)))
      "," (gc:csv (gc:number (nth 1 align-point)))
      "," (gc:csv (gc:number (nth 2 align-point)))
      "," (gc:csv (gc:number hjust))
      "," (gc:csv (gc:number vjust))
      "," (gc:csv (gc:number box-width))
      "," (gc:csv (gc:number attachment))
      "," (gc:csv (gc:number line-style))
      "," (gc:csv (gc:number line-factor))
    )
    file
  )
)

(defun c:GLYPHREPORT (/ selection output file index entity entity-data)
  (prompt "\nSelect TEXT and MTEXT entities to include in the report: ")
  (setq selection (ssget '((0 . "TEXT,MTEXT"))))
  (cond
    ((not selection)
      (prompt "\nNo text entities selected; no report was created.")
    )
    ((not
       (setq output
         (getfiled
           "Save text details report"
           (strcat (getvar "DWGPREFIX") "text-details.txt")
           "txt"
           1
         )
       )
     )
      (prompt "\nReport cancelled.")
    )
    ((not (setq file (open output "w")))
      (prompt (strcat "\nCould not open report file: " output))
    )
    (T
      (write-line
        (strcat
          "\"Handle\",\"Type\",\"Layer\",\"Text\",\"Style\",\"Font file\","
          "\"Big font file\",\"Height\",\"Width factor\",\"Oblique degrees\","
          "\"Rotation degrees\",\"X\",\"Y\",\"Z\",\"Alignment X\","
          "\"Alignment Y\",\"Alignment Z\",\"Horizontal justification\","
          "\"Vertical justification\",\"MTEXT box width\",\"MTEXT attachment\","
          "\"MTEXT line spacing style\",\"MTEXT line spacing factor\""
        )
        file
      )
      (setq index 0)
      (while (< index (sslength selection))
        (setq entity (ssname selection index))
        (setq entity-data (entget entity))
        (gc:write-entity file entity-data)
        (setq index (1+ index))
      )
      (close file)
      (prompt
        (strcat
          "\nWrote "
          (itoa (sslength selection))
          " text record(s) to "
          output
        )
      )
    )
  )
  (princ)
)

(princ "\nGlyph Creator text report loaded. Run GLYPHREPORT to export selected text.")
(princ)
