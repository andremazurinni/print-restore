(Русская версия: README.txt)

Credits:

Reverse-engineering of the Canon CAPT protocol (LBP-810/LBP-1120 printers), 2004:
  (C) Nicolas Boichat <nicolas@boichat.ch>
  based on the work of Rildo Pragana (driver for Samsung ML-85G)
  http://www.boichat.ch/nicolas/capt/
Protocol materials and documentation also drawn from the captdriver project:
  (C) Alexey Galakhov and other contributors
  https://github.com/agalakhov/captdriver

Python port, WinUSB and Ctrl+P integration for Windows, 2026:
  andre_mazurinni

Distributed under the GNU GPL (inherited from the original Boichat/Pragana
source code) - see the COPYING file in this folder.

----------------------------------------------------------------------

What's new in version 55 (Print Restore):
  - A single installer file Print_Restore_Setup_v55.exe with a wizard: it finds the printer by itself
    (LBP-1120 and LBP-810, models can also be chosen manually), no black console windows.
  - Honest result: if setup fails, the last page says "Installation not completed", the reason and
    the log path C:\Program Files\CaptPrinter_Setup\install_output.log.
  - Redmon is now inside the installer (no internet needed for it). Ghostscript is downloaded from
    the official site; without internet a window offers "Open download page" and choosing the
    downloaded file (the "for Windows (64 bit)" version is needed).
  - Test page: checkbox "Print a test page" on the last wizard page, followed by the question
    whether the page printed correctly.
  - Anonymous installation statistics (checkbox, on by default) - see "Installation statistics" below.

What's new in version 54:
  - Support for the Canon LBP-810 printer (USB 04A9:260A): a separate "Canon LBP-810" queue, its own sheet
    and cartridge counter (Counter_810.cmd), a test page labelled LBP-810 with the serial number.
  - Toner saver for the LBP-810 (A4, A5, A6, A7).
  - "Quick preset" list in the print settings (Properties - Advanced): Text, Photo, Toner saver, Draft.
    Works in both settings modes and overrides the other options.
  - Manual duplex: add manual_duplex = 1 to settings.ini. After the first sides a window asks you to turn
    the stack over like a book page (top stays on top, blank side towards you).
  - Skip blank pages (skip_blank_pages = 1), print shift (shift_x_mm, shift_y_mm), thin-line boost
    (thin_lines), all text black (text_black), rotate 180 degrees (rotate180), colour to grey like Windows
    "Black and white" (gray_conversion = luminance). All off by default, described in settings.ini.
  - Notifications and dialogs are now visible when printing through the queue (they were not before).
  - If the printer reports a jam or an open cover, the sheet is not added to the counter.
  - Pictures printed with the right-click menu also go to the LBP-810 (when it is the only one connected,
    or image_printer = 810 in settings.ini).

----------------------------------------------------------------------

Installation on a PC (Python is NOT required):

1. Connect the printer via USB, switch it on and load A4 paper.
2. Run Print_Restore_Setup_v55.exe and click "Yes" in the Windows prompt (administrator rights needed).
3. In the wizard: tick that the printer is connected and paper is loaded; the wizard finds the
   printer by itself (or choose the model manually) and installs everything. If the Ghostscript
   setup window opens, click Next, I Agree, Install, Finish - needed only once.
4. On the last page keep the "Print a test page" checkbox and click "Finish".

The installer by itself: copies capt_print.exe to C:\Program Files\CaptPrinter\, installs
Ghostscript (if missing) and Redmon, creates and signs the printer's WinUSB driver with a
self-signed certificate, registers the Redmon port, creates the printer "Canon LBP-1120"
(and "Canon LBP-810") and installs the "Canon LBP-1120 (CAPT)" driver with the print quality
settings dialog. If two LBP-1120 printers are connected, it also creates a queue for each one
("Canon LBP-1120 (SERIAL NUMBER)") - choose the printer in the print dialog.

When it finishes, the "Canon LBP-1120" printer is available in every print
dialog (Ctrl+P).

Helpers (people installing the driver for others): run with
   Print_Restore_Setup_v55.exe /ROLE=helper /NAME=Name
or put stats.ini next to the installer (lines role=helper and name=Name) - the installation is
counted under the helper's name (see "Installation statistics").

Advanced: the setup files are in C:\Program Files\CaptPrinter_Setup; the setup can be repeated
by hand from an administrator PowerShell: .\setup.ps1

----------------------------------------------------------------------

Print settings (like the Quality tab of the original Canon driver):

Printing Preferences of the printer -> "Advanced" -> section "Printer Properties":

  Settings mode                  Standard (default): every setting below is ignored
                                 and safe values are used - one choice "resets" printing.
                                 Manual: the settings below apply (Windows remembers them).
                                 To make them permanent choose Manual and set the values
                                 in Settings -> Printers -> Printing preferences.
  Print quality / Resolution     600 dpi (default) or 300 dpi
                                 (3-4 times less data)
  Halftoning                     Auto (by content: crisp text, smooth photos, default),
                                 Pattern 1 (clustered dots, like the original
                                 driver), Fine pattern (Bayer 4x4),
                                 Smooth (Floyd-Steinberg),
                                 No halftones (black and white only)
  Toner Density                  Lightest ... Darkest
  Toner Saver                    saves toner
  Automatic Image Refinement     edge smoothing done by the printer
  Brightness, Contrast           -100% .. +100% in 10% steps (done on the PC)

Copies, orientation and paper size come from the regular print settings.
Paper sizes in the list: A4, A5, A6 and A7 (74x105 mm; EXPERIMENTAL - narrower than the printer's
76 mm minimum, feed sheets one at a time and centred in the tray). Any other size (76x127 to
210x297 mm): Advanced -> Paper size -> "PostScript Custom Page Size". To print an A4 Word
document on smaller paper: File -> Print -> "1 Page Per Sheet" -> "Scale to Paper Size".
Printing happens only inside 2 mm margins on the left, right and bottom (about 5 mm at the top
is not printable): frames and lines right at the sheet edge may be lost. A4 prints the same way: 2 mm
margins left and right, printable width 206 mm (verified by scan on 05.10.2026).
Output is 1:1: the driver does not shrink or stretch anything. The scale is set by the application:
- Word: "Scale to Paper Size" must be chosen for every print (Word does not remember it); Windows
  remembers only the driver window options (Settings mode, quality, etc.).
- PDF viewers (Edge, Acrobat, etc.): for an exact size choose "Actual size" (100%), not "Fit to page" -
  otherwise the program shrinks the sheet by about 5% on its own.

Reset settings to defaults: ppd_driver\Reset_print_settings.cmd (asks for
administrator rights).

Fallback settings file: C:\ProgramData\CaptPrinter\settings.ini (same set of
options, used for jobs where the print dialog values were not changed; values
from the print dialog take priority). setup.ps1 installs the driver with the
settings dialog; to install it separately (or again) run
ppd_driver\install_ppd_driver.ps1, log: C:\ProgramData\CaptPrinter\
ppd_install.log, roll back to the standard driver: install_ppd_driver.ps1 -Rollback.

Additional settings in settings.ini (version v44; lines starting with ; are comments; applied from the next
job, no restart needed):
  tone_correction = 1       compensation for dark mid-tones (0 - off)
  tone_strength = 50        compensation strength, 0-100 % (50 - smooth gradients and distinguishable dark tones)
  printer_serial =          printer serial number when two or more printers are connected (empty - first found)
  photo_valign = top        photo position when printing an image (print_image_context.py): top / center / bottom
  photo_halign = center     horizontal: left / center / right
  photo_fit = full          full - photo on the whole sheet; shrink - reduce the photo until it prints in the smooth mode
If a page is too dense for the printer (otherwise printing is cut off in the middle of the sheet), the driver
simplifies the print mode by itself; if a cut-off still happens, a notification "Page printed partially" appears.

If a page does not fit (more than 2.5 MB of data), the mode is simplified
automatically: Floyd-Steinberg -> smart -> ordered -> screen -> with blur -> black and
white threshold. The chosen mode and data size are written to
C:\ProgramData\CaptPrinter\capt_redmon.log.

For photos with very light details, do not print straight from the Photos app
(Windows cuts light details when printing images through GDI); put the image
into a document (Word) or save it as PDF and print the PDF.

----------------------------------------------------------------------

If automatic printer creation failed (the wizard said "Installation not completed", the reason
is in C:\Program Files\CaptPrinter_Setup\install_output.log) and running the installer again does
not help, the fallback is the standard Windows wizard:

1. Control Panel -> Devices and Printers -> Add a printer
   -> "The printer that I want isn't listed"
   -> "Add a local printer or network printer with manual settings"
2. Port: "Create a new port" -> type "Redirected Port" -> name RPT1: -> OK
3. Driver: "Generic" -> "MS Publisher Imagesetter" -> Next.
   IMPORTANT: NOT "Microsoft" -> "Microsoft PS Class Driver" - incompatible with Redmon.
4. "Do not share this printer" -> Next -> Finish (no test page).
5. Printer properties -> Ports -> RPT1: -> "Configure Port":
     Redirect this port to the program: C:\Program Files\CaptPrinter\capt_print.exe
     Arguments for this program are:    --dithering ordered
     Output: Program handles output
   If you get "Invalid function", open the same window from an administrator
   PowerShell: rundll32 printui.dll,PrintUIEntry /p /n "MS Publisher Imagesetter"

Then run ppd_driver\install_ppd_driver.ps1 (the quality settings dialog).

----------------------------------------------------------------------

Sheet counter and cartridge life:
  The printer has no counter or toner sensor of its own, so the driver counts the sheets
  (file C:\ProgramData\CaptPrinter\counter.json; only jobs printed through this driver are
  counted). View and reset: C:\Program Files\CaptPrinter\Counter.cmd (Enter - close, R - cartridge
  replaced, reset). The default rated life is 2500 sheets (Canon EP-22, 5% coverage; use your
  own value for a refilled/other cartridge): printer_counter.ps1 -Rated 3000.
  If the cartridge is already partly used: printer_counter.ps1 -Since 700.
  At 80%, 95% and 100% of the rated life the driver shows a Windows notification once, with a
  "Cartridge replaced - reset" button (one click, no scripts). Fallback without the notification:
  Printing Preferences -> Advanced -> "Cartridge counter" -> "Cartridge replaced - reset...";
  the counter resets on the next print, then set the row back to "Keep".
  Real consumption depends on page coverage and density, so this is an estimate.

If printing does not work (antivirus, blocking, etc.):

First look at the log: C:\ProgramData\CaptPrinter\capt_redmon.log. If NO new
lines appear in it after you send a job, capt_print.exe did not start at all -
an antivirus or SmartScreen is blocking it (the file has no reputation with
antivirus programs: it is built by the project itself and signed with a
self-signed certificate). What to do:

1. Check that C:\Program Files\CaptPrinter\capt_print.exe exists. If it does not, an antivirus
   removed it or put it in quarantine: restore it from the quarantine / the
   protection history (Windows Security -> Virus & threat protection ->
   Protection history) or run the Print Restore installer again.
2. Add the folder to the Windows Defender exclusions (PowerShell as administrator):
     Add-MpPreference -ExclusionPath "C:\Program Files\CaptPrinter"
   For a third-party antivirus add C:\Program Files\CaptPrinter and
   C:\Program Files\CaptPrinter_Setup to its exclusions manually.
3. If the file is marked as downloaded from the internet and does not start:
     Unblock-File "C:\Program Files\CaptPrinter\capt_print.exe"
   (or right click the file -> Properties -> "Unblock").
4. Fallback without the exe - through Python: install Python 3.10+
   (python.org, check "Add python.exe to PATH") and in C:\Program Files\CaptPrinter_Setup
   (administrator PowerShell) run:
     .\setup.ps1 -UsePython
   It connects the printer to the Python scripts in that folder (no
   capt_print.exe needed). If capt_print.exe is missing and Python is
   installed, setup.ps1 switches to this mode by itself.
5. Other common causes: the printer is off or not connected by USB; the printer
   is held by another program (for example a virtual machine with USB
   passthrough); USB hub problems (connect directly to the PC); on Windows 11
   24H2+ Windows Protected Print Mode is enabled (turn it off); Ghostscript or
   Redmon were not installed (run the installer again).

----------------------------------------------------------------------

Source code: for those who want to read or change the code (GNU GPL, see COPYING).
Not needed for a normal installation. All Python scripts are in the setup folder
C:\Program Files\CaptPrinter_Setup next to setup.ps1 (capt_print2.py, capt_print_pdf.py,
capt_print_redmon.py, capt_counter.py, and also jpg_to_pdf.py and print_image_context.py -
right-click image printing, not connected by the installer). capt_print.exe is built from
these files with PyInstaller; to build it yourself, see BUILD.txt (capt_print.spec is
in the same folder).

Uninstall: Windows Settings -> Apps -> Print Restore -> Uninstall (or Start -> Print Restore ->
"Uninstall Print Restore"). Printers, ports, driver and files are removed; Ghostscript and Redmon
only if this installer put them there and nothing else uses them. Settings (settings.ini) and the
sheet counter stay in C:\ProgramData\CaptPrinter for a reinstall.
By hand (administrator PowerShell, in the setup folder):
  .\uninstall.ps1        (or .\uninstall.ps1 -Full - together with Ghostscript, Redmon, the certificate)

----------------------------------------------------------------------

Technical requirements for the target PC:

- Operating system: Windows 8.1, 10 or 11, 64-bit (x64).
  On Windows 8.1 (PowerShell 4) setup and printing work; only the optional driver
  with the advanced quality settings dialog is not installed (needs PowerShell 5+)
  - the printer works with the standard driver.
- Python is not needed (it is packed inside capt_print.exe).
- Administrator rights during installation (driver, Ghostscript, Redmon, printer).
- A free USB port: connect the printer directly to a PC port, not through a
  cheap passive USB hub.
- Internet during installation is needed only for Ghostscript, if it is not on the PC yet:
  the installer downloads it from the official site (github.com/ArtifexSoftware) and checks
  the file - its SHA-256 hash or a genuine Artifex digital signature. If the download fails,
  a window opens: "Open download page" (ghostscript.com, row "Ghostscript ... for Windows
  (64 bit)", link "Ghostscript AGPL Release"), then "Choose file..." - the chosen file is
  checked too, and a file without the Artifex signature is not run. Redmon (redmon19.zip, GPL licence) is inside the installer and is checked by
  its hash. The printer's WinUSB driver (our own development) does not access the internet.
- On Windows 11 24H2+ with Windows Protected Print Mode enabled, the
  third-party Redmon port monitor does not work - disable this mode if
  printing fails.

Installer integrity check: compare the SHA-256 of the file with the one
published separately from it (PowerShell):
  Get-FileHash Print_Restore_Setup_v55.exe -Algorithm SHA256
If the hash does not match, do not run it - the file may have been replaced.

----------------------------------------------------------------------

Installation statistics (anonymous):

If the checkbox "Anonymously count this installation for statistics and support" on the
printer connection page is left on (it is on by default), one short report is sent at the
end of the installation to the developer's server https://stat.tat-paket.ru. It shows how
many installations were made and at which step they fail. What is sent:
  - a random installation number (created once and kept in the registry at
    HKLM\SOFTWARE\PrintRestore; it stays after uninstalling, so a reinstall on the same
    computer counts as one installation);
  - printer models (for example 1120, 810) and their USB model IDs (262B, 260A);
  - the driver version and the Windows build number;
  - the result (success or error), the failed step and its code;
  - for helpers (/ROLE=helper) - the helper name given.
NOT sent: the computer and user names, printer serial numbers, MAC address, documents.
The server does not store IP addresses. Without internet the report is saved to
C:\ProgramData\CaptPrinter\pending.json and sent with the next installation.

How to turn it off: untick the checkbox on the printer connection page, or run the
installer with the /NOSTATS parameter. To remove the installation number from the computer
(administrator PowerShell or command prompt):
  reg delete "HKLM\SOFTWARE\PrintRestore" /f
