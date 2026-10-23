; Canon LBP-1120 / LBP-810 - single-file installer (Inno Setup), ЧЕРНОВИК v55dev.
; Основа: LBP1120_InnoSetup_v54.iss (не изменён). Добавлено только в мастере:
;   1) страница "Подключите принтер" с галочкой (Далее неактивна, пока не отмечена);
;   2) страница поиска принтера по VID 04A9 + PID из таблицы (WMI Win32_PnPEntity);
;   3) анимация 12 BMP-кадров над полосой прогресса;
;   4) галочка "Напечатать тестовую страницу" на последней странице.
; Логика драйвера (Install.cmd / setup.ps1) не менялась.

#define MyAppName "Print Restore"
#define MyAppVersion "55"
#ifndef FramesDir
  #define FramesDir "D:\Distrib\LBP1120\github_staging_2026-10-13\installer\frames"
#endif

[Setup]
AppName={#MyAppName}
; Авторство: показывается в "Программы и компоненты" (издатель) и в свойствах файла установщика. Ссылка - на блог Boosty (Telegram автор не хочет показывать).
AppPublisher=Andrey Mazur
AppPublisherURL=https://boosty.to/printrestore
AppSupportURL=https://boosty.to/printrestore
AppCopyright=Copyright (C) 2026 Andrey Mazur
VersionInfoVersion=55.0.0.0
VersionInfoCompany=Andrey Mazur
VersionInfoCopyright=Copyright (C) 2026 Andrey Mazur
VersionInfoProductName=Print Restore
VersionInfoDescription=Print Restore - driver installer for Canon LBP printers
; Ключ удаления в реестре остаётся прежним (как у v54), чтобы v55 ставилась поверх, а не рядом.
AppId=Canon LBP-1120
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\CaptPrinter_Setup
DefaultGroupName=Print Restore
DisableProgramGroupPage=yes
DisableDirPage=yes
; Перезагрузка не нужна: печать работает сразу. Без этой строки мастер просит перезагрузку, если установщик Ghostscript оставил пометку.
RestartIfNeededByRun=no
OutputDir=D:\Distrib\LBP1120\releases
OutputBaseFilename=Print_Restore_Setup_v{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
SetupLogging=yes
DisableWelcomePage=no
WizardStyle=modern
SetupIconFile=assets\printrestore.ico
UninstallDisplayIcon={app}\printrestore.ico

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
russian.WelcomeLabel2=Программа установит драйвер для вашего принтера на ваш компьютер.%n%nРекомендуется закрыть все прочие приложения перед тем, как продолжить.%n%nНажмите «Далее», чтобы продолжить, или «Отмена», чтобы выйти из программы установки.%n%nPrint Restore © 2026 Andrey Mazur, https://boosty.to/printrestore%nОснован на captdriver (GPL).
english.WelcomeLabel2=This will install the driver for your printer on your computer.%n%nIt is recommended that you close all other applications before continuing.%n%nClick Next to continue, or Cancel to exit Setup.%n%nPrint Restore (c) 2026 Andrey Mazur, https://boosty.to/printrestore%nBased on captdriver (GPL).

[CustomMessages]
russian.Installing=Устанавливаю Print Restore (драйвер для принтеров Canon LBP)... Дождитесь окончания. Если откроется окно установки Ghostscript, следуйте его подсказкам.
russian.FoundAuto=Найден принтер: %1
russian.FoundAutoHint=Если это не ваш принтер, выберите модель вручную.
russian.BtnAuto=Определить автоматически
russian.UninstLang=ru
russian.MemoPrinters=Принтеры для установки:
russian.GsNote=Дальше откроется окно установки Ghostscript (на английском, оно появится поверх остальных). Нажимайте в нём: Next, I Agree, Install, а в конце Finish. Это нужно один раз.
russian.WppNote=ВНИМАНИЕ: включён «Режим защищённой печати Windows». С ним Print Restore работать не может. Выключите его: Параметры -> Bluetooth и устройства -> Принтеры и сканеры -> Режим защищённой печати Windows -> Отключить. Затем запустите установку снова.
russian.ConnCaption=Подключение принтера
russian.ConnSub=Перед установкой принтер должен быть подключён и включён
russian.ConnText=Подключите принтер к USB-порту компьютера и включите его.%n%nКогда принтер включён, отметьте галочки ниже.%n%nЗагрузите бумагу A4 в лоток: в конце установки можно напечатать пробную страницу (галочка на последней странице).
russian.ConnCheck=Принтер подключён и включён
russian.PaperCheck=Бумага A4 загружена в лоток
russian.DetCaption=Поиск принтера
russian.DetSub=Определяем модель подключённого принтера
russian.NotFound=Принтер не определён. Проверьте USB-кабель и питание принтера.
russian.FoundOne=Найден %1. Это ваш принтер?
russian.FoundMany=Найдено несколько принтеров. Отметьте те, которые нужно установить:
russian.PickManual=Отметьте модели, которые нужно установить:
russian.BtnYes=Да, это мой принтер
russian.BtnManual=Выбрать вручную
russian.BtnRetry=Повторить поиск
russian.Confirmed=Выбран принтер: %1.
russian.NotPresent=Один из выбранных принтеров сейчас не подключён: драйвер установится только для подключённых принтеров.
russian.Unverified=Эта модель ещё не проверена, печать может не заработать.
russian.UnverifiedTag= (не проверено)
russian.StatsCheck=Анонимно учитывать установку для статистики и поддержки
russian.StatsNote=Передаётся: модель принтера, версия драйвера и Windows, результат установки и случайный номер установки. Имя компьютера, имя пользователя, серийные номера и ваши документы не передаются.
russian.StatsMemoOn=Учёт установки: включён (обезличенно)
russian.StatsMemoOff=Учёт установки: отключён
russian.TestPrintCheck=Напечатать тестовую страницу
russian.ProgDetect=Проверяю подключение принтера
russian.ProgCopy=Копирую файлы драйвера
russian.ProgGs=Ghostscript: проверяю и при необходимости скачиваю. Если откроется его окно - нажимайте Next, I Agree, Install, Finish
russian.ProgRedmon=Устанавливаю Redmon (монитор портов печати)
russian.ProgDriver=Устанавливаю драйвер принтера (WinUSB)
russian.ProgQueue=Создаю принтеры
russian.ProgPpd=Устанавливаю окно настроек качества печати
russian.ProgDone=Завершаю установку
russian.ProgElapsed=прошло
russian.FailHeading=Установка не завершена
russian.FailText=Принтер НЕ установлен.%n%n%1%n%nЖурнал: %2
russian.FailGs=Не удалось получить или установить Ghostscript. Проверьте подключение к интернету.
russian.FailRm=Не удалось установить Redmon (монитор портов печати). Подробности - в журнале.
russian.FailWpp=Включён «Режим защищённой печати Windows»: с ним сторонние драйверы принтеров не работают.%nВыключите его: Параметры -> Bluetooth и устройства -> Принтеры и сканеры -> Режим защищённой печати Windows -> Отключить. Затем запустите установку снова.
russian.FailGeneric=Во время установки произошла ошибка.
english.Installing=Installing Print Restore (driver for Canon LBP printers)... Please wait. If the Ghostscript setup window opens, follow its prompts.
english.FoundAuto=Printer found: %1
english.FoundAutoHint=If this is not your printer, choose the model manually.
english.BtnAuto=Detect automatically
english.UninstLang=en
english.MemoPrinters=Printers to install:
english.GsNote=Next, the Ghostscript setup window will open (it will appear on top of other windows). Click: Next, I Agree, Install, and Finish at the end. This is needed only once.
english.WppNote=WARNING: Windows protected print mode is on. Print Restore cannot work with it. Turn it off: Settings -> Bluetooth & devices -> Printers & scanners -> Windows protected print mode -> Turn off. Then run the installation again.
english.ConnCaption=Connect the printer
english.ConnSub=The printer must be connected and switched on before installation
english.ConnText=Connect the printer to a USB port and switch it on.%n%nWhen the printer is on, tick the boxes below.%n%nLoad A4 paper into the tray: at the end of the installation you can print a test page (checkbox on the last page).
english.ConnCheck=The printer is connected and switched on
english.PaperCheck=A4 paper is loaded in the tray
english.DetCaption=Finding the printer
english.DetSub=Detecting the connected printer model
english.NotFound=Printer not detected. Check the USB cable and the printer power.
english.FoundOne=Found %1. Is this your printer?
english.FoundMany=Several printers found. Tick the ones to install:
english.PickManual=Tick the models to install:
english.BtnYes=Yes, this is my printer
english.BtnManual=Choose manually
english.BtnRetry=Search again
english.Confirmed=Selected printer: %1.
english.NotPresent=One of the selected printers is not connected now: the driver will be installed only for connected printers.
english.Unverified=This model has not been tested yet, printing may not work.
english.UnverifiedTag= (not tested)
english.StatsCheck=Anonymously count this installation for statistics and support
english.StatsNote=Sent: printer model, driver and Windows version, installation result and a random installation number. Computer name, user name, serial numbers and your documents are not sent.
english.StatsMemoOn=Installation statistics: on (anonymous)
english.StatsMemoOff=Installation statistics: off
english.TestPrintCheck=Print a test page
english.ProgDetect=Checking the printer connection
english.ProgCopy=Copying the driver files
english.ProgGs=Ghostscript: checking and downloading if needed. If its window opens, click Next, I Agree, Install, Finish
english.ProgRedmon=Installing Redmon (print port monitor)
english.ProgDriver=Installing the printer driver (WinUSB)
english.ProgQueue=Creating the printers
english.ProgPpd=Installing the print quality settings dialog
english.ProgDone=Finishing the installation
english.ProgElapsed=elapsed
english.FailHeading=Installation not completed
english.FailText=The printer is NOT installed.%n%n%1%n%nLog: %2
english.FailGs=Could not download or install Ghostscript. Check your internet connection.
english.FailRm=Could not install Redmon (print port monitor). See the log for details.
english.FailWpp=Windows protected print mode is on: third-party printer drivers do not work with it.%nTurn it off: Settings -> Bluetooth & devices -> Printers & scanners -> Windows protected print mode -> Turn off. Then run the installation again.
english.FailGeneric=An error occurred during installation.

[Files]
; Install_AnyDesk.cmd не кладём: в папке установки он запустил бы setup.ps1 -SelfDestruct, а тот удаляет всю папку вместе
; с деинсталлятором (аудит 22.10.2026, F2). Файл нужен только для старой ZIP-раздачи через AnyDesk.
Source: "LBP1120_Portable_v55dev\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion; Excludes: "__pycache__\*,Install_AnyDesk.cmd"
Source: "assets\printrestore.ico"; DestDir: "{app}"; Flags: ignoreversion
; Метка помощника для статистики (/ROLE=helper /NAME=Имя или stats.ini рядом с установщиком): мастер собирает файл во временной папке.
Source: "{tmp}\stats.ini"; DestDir: "{app}"; Flags: external ignoreversion; Check: HelperMode
; Кадры анимации: в установленные файлы не копируются, достаются во временную папку мастера.
; Логотип CAPT, который летает поверх мамонтов: векторная трассировка скана, маски пяти размеров под масштаб экрана
; (серый = 255 - непрозрачность буквы). Исходник - assets\capt_logo_vector.svg, скрипт - assets\trace_capt.py.
Source: "assets\capt_logo_100.bmp"; Flags: dontcopy
Source: "assets\capt_logo_125.bmp"; Flags: dontcopy
Source: "assets\capt_logo_150.bmp"; Flags: dontcopy
Source: "assets\capt_logo_175.bmp"; Flags: dontcopy
Source: "assets\capt_logo_200.bmp"; Flags: dontcopy
Source: "{#FramesDir}\f1.bmp";  Flags: dontcopy
Source: "{#FramesDir}\f2.bmp";  Flags: dontcopy
Source: "{#FramesDir}\f3.bmp";  Flags: dontcopy
Source: "{#FramesDir}\f4.bmp";  Flags: dontcopy
Source: "{#FramesDir}\f5.bmp";  Flags: dontcopy
Source: "{#FramesDir}\f6.bmp";  Flags: dontcopy
Source: "{#FramesDir}\f7.bmp";  Flags: dontcopy
Source: "{#FramesDir}\f8.bmp";  Flags: dontcopy
Source: "{#FramesDir}\f9.bmp";  Flags: dontcopy
Source: "{#FramesDir}\f10.bmp"; Flags: dontcopy
Source: "{#FramesDir}\f11.bmp"; Flags: dontcopy
Source: "{#FramesDir}\f12.bmp"; Flags: dontcopy

[InstallDelete]
; Метка помощника не должна переходить на другую установку поверх: обычный клиент старый stats.ini не наследует.
Type: files; Name: "{app}\stats.ini"; Check: not HelperMode
; от прежних установок v55 (до 22.10.2026) в папке мог остаться Install_AnyDesk.cmd - убираем (аудит F2)
Type: files; Name: "{app}\Install_AnyDesk.cmd"

[Icons]
Name: "{group}\Инструкция (README)"; Filename: "{app}\README.txt"; Languages: "russian"
Name: "{group}\Instructions (README)"; Filename: "{app}\README_EN.txt"; Languages: "english"
Name: "{group}\Счётчик картриджа"; Filename: "{app}\Counter.cmd"; WorkingDir: "{app}"; Languages: "russian"
Name: "{group}\Cartridge counter"; Filename: "{app}\Counter.cmd"; WorkingDir: "{app}"; Languages: "english"
Name: "{group}\Удалить Print Restore"; Filename: "{uninstallexe}"; Languages: "russian"
Name: "{group}\Uninstall Print Restore"; Filename: "{uninstallexe}"; Languages: "english"

; Запуск setup.ps1 перенесён из [Run] в код (RunSetupScript, шаг ssPostInstall): [Run] не видит код возврата, и при сбое
; мастер всё равно писал "Установка завершена". Теперь код возврата проверяется и итог на последней странице честный.
;
; Галочка "Напечатать тестовую страницу" на последней странице: postinstall-запись запускает тот же setup.ps1 с -TestOnly.
; Показывается только при успешной установке; в тихом режиме не запускается (вопрос "напечаталось?" зависнул бы без пользователя).
[Run]
Filename: "{cmd}"; Parameters: "/c powershell.exe -NoProfile -ExecutionPolicy Bypass -File ""{app}\setup.ps1"" -Lang {cm:UninstLang} -Models ""{code:ModelsParam}"" -TestOnly >> ""{app}\install_cmd.log"" 2>&1"; WorkingDir: "{app}"; Flags: postinstall nowait runhidden skipifsilent runascurrentuser; Description: "{cm:TestPrintCheck}"; Check: InstallSucceeded

[UninstallRun]
; Удаление без чёрного окна: тот же uninstall.ps1 напрямую (Uninstall.cmd заканчивается pause и завис бы).
; Язык (ru/en) передаётся параметром, окно выбора языка не показывается. Вывод - в %TEMP%\PrintRestore_uninstall.log.
Filename: "{cmd}"; Parameters: "/c chcp 65001 >nul & powershell.exe -NoProfile -ExecutionPolicy Bypass -File ""{app}\uninstall.ps1"" -Lang {cm:UninstLang} > ""{%TEMP}\PrintRestore_uninstall.log"" 2>&1"; WorkingDir: "{app}"; Flags: waituntilterminated runhidden; RunOnceId: "RemoveLBP1120Driver"; MinVersion: 10.0
Filename: "{cmd}"; Parameters: "/c powershell.exe -NoProfile -ExecutionPolicy Bypass -File ""{app}\uninstall.ps1"" -Lang {cm:UninstLang} > ""{%TEMP}\PrintRestore_uninstall.log"" 2>&1"; WorkingDir: "{app}"; Flags: waituntilterminated runhidden; RunOnceId: "RemoveLBP1120Driver"; OnlyBelowVersion: 10.0

[UninstallDelete]
; Журнал установки создаётся после копирования файлов и Inno о нём не знает.
Type: files; Name: "{app}\install_output.log"
Type: files; Name: "{app}\install_cmd.log"
; Папка установки наша (служебные файлы Print Restore): убираем целиком, вместе с остатками от прошлых версий, которые Inno не отслеживает.
Type: filesandordirs; Name: "{app}"

[Code]
function SetTimer(hWnd, nIDEvent, uElapse, lpTimerFunc: LongWord): LongWord; external 'SetTimer@user32.dll stdcall';
function KillTimer(hWnd, uIDEvent: LongWord): LongWord; external 'KillTimer@user32.dll stdcall';

// ---------------------------------------------------------------------------
// Таблица моделей. Новая модель = ОДНА строка AddModel(...) в InitModels.
// Параметры: название, PID (hex, VID всегда 04A9), проверено ли (True/False).
// ---------------------------------------------------------------------------
type
  TModel = record
    Name: String;
    Pid: String;
    Verified: Boolean;
  end;

  TFound = record
    ModelIdx: Integer;
    DevId: String;
  end;

var
  Models: array of TModel;
  Selected: array of Boolean;      // отмечена ли модель (индекс как в Models)
  Found: array of TFound;          // найденные USB-устройства
  FoundModels: array of Integer;   // различные модели среди найденных
  Checks: array of TNewCheckBox;
  Frames: array[0..11] of TBitmap;
  DetMode: Integer;                // 0 не найден, 1 одна модель, 2 несколько
  ConnPage, DetPage: TWizardPage;
  ConnCheck, PaperCheck: TNewCheckBox;
  DetMsg, DetWarn: TNewStaticText;
  BtnRetry: TNewButton;
  AnimImg: TBitmapImage;
  LastFrame: Integer;
  TimerId, PollId: LongWord;
  DetSig: String;

// Режим защищённой печати Windows 11 (переключатель в Параметрах пишет сюда WindowsProtectedPrintMode = 1).
// С ним сторонний монитор портов Redmon не ставится, печать невозможна.
function WppEnabled: Boolean;
var
  v: Cardinal;
begin
  Result := RegQueryDWordValue(HKLM64, 'SOFTWARE\Policies\Microsoft\Windows NT\Printers\WPP', 'WindowsProtectedPrintMode', v) and (v = 1);
end;

function GsInstalled: Boolean;
var
  R: TFindRec;
  base: String;
begin
  Result := False;
  base := ExpandConstant('{commonpf64}\gs\');
  if FindFirst(base + 'gs*', R) then
  begin
    try
      repeat
        if FileExists(base + R.Name + '\bin\gswin64c.exe') then Result := True;
      until Result or not FindNext(R);
    finally
      FindClose(R);
    end;
  end;
end;

procedure AddModel(const AName, APid: String; AVerified: Boolean);
var
  n: Integer;
begin
  n := GetArrayLength(Models);
  SetArrayLength(Models, n + 1);
  SetArrayLength(Selected, n + 1);
  Models[n].Name := AName;
  Models[n].Pid := APid;
  Models[n].Verified := AVerified;
  Selected[n] := False;
end;

procedure InitModels;
begin
  AddModel('LBP-1120',          '262B', True);
  AddModel('LBP-810',           '260A', True);
  // Будущие модели - одной строкой, когда для них появится поддержка в драйвере:
  //   AddModel('LBP-1210',          '2617', False);
  //   AddModel('LBP-3200',          '2636', False);
  //   AddModel('LBP3100/3108/3150', '26DB', False);
  //   AddModel('LBP3210',           '2657', False);
  //   AddModel('LBP3600',           '2654', False);
end;

function FindModelByPid(const APid: String): Integer;
var
  i: Integer;
begin
  Result := -1;
  for i := 0 to GetArrayLength(Models) - 1 do
    if CompareText(Models[i].Pid, APid) = 0 then
    begin
      Result := i;
      Exit;
    end;
end;

// Отмеченные модели (PID через запятую) - параметр -Models для setup.ps1.
// Пусто (например, тихая установка без мастера) = ставить всё подключённое.
function ModelsParam(Param: String): String;
var
  i: Integer;
begin
  Result := '';
  for i := 0 to GetArrayLength(Models) - 1 do
    if Selected[i] then
    begin
      if Result <> '' then Result := Result + ',';
      Result := Result + Models[i].Pid;
    end;
end;

// ---------------------------------------------------------------------------
// Статистика установок. Клиент: галочка на странице подключения (по умолчанию включена), при отказе
// в setup.ps1 уходит -NoStats. Помощник: /ROLE=helper /NAME=Имя или stats.ini рядом с установщиком
// (role=helper, name=Имя); галочки нет, отправка всегда. Тихая установка: /NOSTATS отключает отправку.
// ---------------------------------------------------------------------------
var
  HelperOn: Boolean;
  StatsCheck: TNewCheckBox;
  StatsNote: TNewStaticText;

function HelperMode: Boolean;
begin
  Result := HelperOn;
end;

function HasSwitch(const AName: String): Boolean;
var
  i: Integer;
begin
  Result := False;
  for i := 1 to ParamCount do
    if CompareText(ParamStr(i), '/' + AName) = 0 then Result := True;
end;

function IniValue(const Lines: TArrayOfString; const AKey: String): String;
var
  i, p: Integer;
  s: String;
begin
  Result := '';
  for i := 0 to GetArrayLength(Lines) - 1 do
  begin
    s := Trim(Lines[i]);
    p := Pos('=', s);
    if (p > 1) and (CompareText(Trim(Copy(s, 1, p - 1)), AKey) = 0) then
    begin
      Result := Trim(Copy(s, p + 1, Length(s)));
      Exit;
    end;
  end;
end;

procedure InitStats;
var
  role, nm, src: String;
  lines, outLines: TArrayOfString;
begin
  HelperOn := False;
  role := Lowercase(Trim(ExpandConstant('{param:ROLE|}')));
  nm := Trim(ExpandConstant('{param:NAME|}'));
  src := ExpandConstant('{src}\stats.ini');
  if role <> '' then
  begin
    if role = 'helper' then
    begin
      SetArrayLength(outLines, 2);
      outLines[0] := 'role=helper';
      outLines[1] := 'name=' + nm;
      HelperOn := SaveStringsToUTF8File(ExpandConstant('{tmp}\stats.ini'), outLines, False);
    end;
  end
  else if FileExists(src) and LoadStringsFromFile(src, lines) then
  begin
    if Lowercase(IniValue(lines, 'role')) = 'helper' then
      HelperOn := FileCopy(src, ExpandConstant('{tmp}\stats.ini'), False);   // копируем как есть: имя может быть кириллицей
  end;
end;

// Параметр для setup.ps1: у клиента, отказавшегося от учёта, -NoStats. У помощника всегда пусто.
function StatsParams(Param: String): String;
begin
  Result := '';
  if HelperOn then Exit;
  if HasSwitch('NOSTATS') or ((StatsCheck <> nil) and (not StatsCheck.Checked)) then Result := '-NoStats';
end;

function SelectedCount: Integer;
var
  i: Integer;
begin
  Result := 0;
  for i := 0 to GetArrayLength(Models) - 1 do
    if Selected[i] then Result := Result + 1;
end;

function ModelPresent(MI: Integer): Boolean;
var
  i: Integer;
begin
  Result := False;
  for i := 0 to GetArrayLength(Found) - 1 do
    if Found[i].ModelIdx = MI then Result := True;
end;

// ---------------------------------------------------------------------------
// Поиск принтеров СЕЙЧАС подключённых (Win32_PnPEntity перечисляет только
// присутствующие устройства, не историю из реестра).
// ---------------------------------------------------------------------------
procedure DetectPrinters;
var
  Loc, Svc, Res, Obj: Variant;
  i, n, k, j, mi: Integer;
  id: String;
  dup: Boolean;
begin
  SetArrayLength(Found, 0);
  SetArrayLength(FoundModels, 0);
  DetSig := '';
  try
    Loc := CreateOleObject('WbemScripting.SWbemLocator');
    Svc := Loc.ConnectServer('.', 'root\cimv2');
    Res := Svc.ExecQuery('SELECT PNPDeviceID FROM Win32_PnPEntity WHERE PNPDeviceID LIKE ''USB\\VID_04A9&PID_%''');
    n := Res.Count;
    for i := 0 to n - 1 do
    begin
      Obj := Res.ItemIndex(i);
      id := Uppercase(Obj.PNPDeviceID);
      // USB\VID_04A9&PID_262B\<serial>: берём PID, составные интерфейсы (&MI_) пропускаем
      if (Length(id) > 21) and (id[22] = '\') then
      begin
        mi := FindModelByPid(Copy(id, 18, 4));
        if mi >= 0 then
        begin
          k := GetArrayLength(Found);
          SetArrayLength(Found, k + 1);
          Found[k].ModelIdx := mi;
          Found[k].DevId := id;
          DetSig := DetSig + id + ';';
          dup := False;
          for j := 0 to GetArrayLength(FoundModels) - 1 do
            if FoundModels[j] = mi then dup := True;
          if not dup then
          begin
            k := GetArrayLength(FoundModels);
            SetArrayLength(FoundModels, k + 1);
            FoundModels[k] := mi;
          end;
        end;
      end;
    end;
  except
    Log('WMI printer detection failed: ' + GetExceptionMessage);
    SetArrayLength(Found, 0);
    SetArrayLength(FoundModels, 0);
  end;
  Log('Printers found: ' + IntToStr(GetArrayLength(Found)));
end;

// ---------------------------------------------------------------------------
// Страница 2: поиск и выбор
// ---------------------------------------------------------------------------
procedure UpdateNextAndWarn;
var
  i: Integer;
  notPresent, unverified: Boolean;
begin
  notPresent := False;
  unverified := False;
  for i := 0 to GetArrayLength(Models) - 1 do
    if Selected[i] then
    begin
      if not ModelPresent(i) then notPresent := True
      else if not Models[i].Verified then unverified := True;
    end;
  if notPresent then DetWarn.Caption := CustomMessage('NotPresent')
  else if unverified then DetWarn.Caption := CustomMessage('Unverified')
  else DetWarn.Caption := '';
  if (DetPage <> nil) and (WizardForm.CurPageID = DetPage.ID) then
    WizardForm.NextButton.Enabled := (SelectedCount > 0);
end;

procedure ClearChecks;
var
  i: Integer;
begin
  for i := 0 to GetArrayLength(Checks) - 1 do
    Checks[i].Free;
  SetArrayLength(Checks, 0);
end;

procedure CheckClick(Sender: TObject);
begin
  Selected[TNewCheckBox(Sender).Tag] := TNewCheckBox(Sender).Checked;
  UpdateNextAndWarn;
end;

procedure AddCheck(ModelIdx, Y: Integer; AChecked: Boolean);
var
  n: Integer;
  cb: TNewCheckBox;
begin
  cb := TNewCheckBox.Create(DetPage);
  cb.Parent := DetPage.Surface;
  cb.Left := 0;
  cb.Top := Y;
  cb.Width := DetPage.SurfaceWidth;
  cb.Height := ScaleY(18);
  cb.Caption := Models[ModelIdx].Name;
  if not Models[ModelIdx].Verified then
    cb.Caption := cb.Caption + CustomMessage('UnverifiedTag');
  cb.Tag := ModelIdx;
  cb.Checked := AChecked;
  Selected[ModelIdx] := AChecked;
  cb.OnClick := @CheckClick;
  n := GetArrayLength(Checks);
  SetArrayLength(Checks, n + 1);
  Checks[n] := cb;
end;

procedure RefreshDetectUI;
var
  i, y: Integer;
begin
  ClearChecks;
  for i := 0 to GetArrayLength(Models) - 1 do
    Selected[i] := False;
  y := ScaleY(104);
  case DetMode of
    0: DetMsg.Caption := CustomMessage('NotFound');
    1: begin
         // Одна модель: сразу считаем её выбранной, "Далее" доступна без лишних нажатий.
         Selected[FoundModels[0]] := True;
         DetMsg.Caption := FmtMessage(CustomMessage('FoundAuto'), [Models[FoundModels[0]].Name]);
       end;
    2: begin
         // Несколько моделей: все найденные отмечены, лишние можно снять.
         DetMsg.Caption := CustomMessage('FoundMany');
         for i := 0 to GetArrayLength(FoundModels) - 1 do
         begin
           AddCheck(FoundModels[i], y, True);
           y := y + ScaleY(22);
         end;
       end;
  end;
  UpdateNextAndWarn;
end;

procedure RunDetection;
begin
  DetectPrinters;
  case GetArrayLength(FoundModels) of
    0: DetMode := 0;
    1: DetMode := 1;
  else
    DetMode := 2;
  end;
  RefreshDetectUI;
end;

// Список принтеров обновляется сам раз в 2 с, пока открыта страница поиска:
// подключили или включили принтер позже - он появится без нажатия кнопок.
procedure PollTimerProc(h, msg, id, t: LongWord);
var
  old: String;
begin
  if (DetPage <> nil) and (WizardForm.CurPageID = DetPage.ID) then
  begin
    old := DetSig;
    DetectPrinters;
    if DetSig <> old then RunDetection;
  end;
end;

procedure BtnRetryClick(Sender: TObject);
begin
  RunDetection;
end;

procedure ConnCheckClick(Sender: TObject);
begin
  WizardForm.NextButton.Enabled := ConnCheck.Checked and PaperCheck.Checked;
end;

function MakeButton(ALeft: Integer; const ACaption: String; AOnClick: TNotifyEvent): TNewButton;
begin
  Result := TNewButton.Create(DetPage);
  Result.Parent := DetPage.Surface;
  Result.Left := ALeft;
  Result.Top := ScaleY(70);
  Result.Width := ScaleX(150);
  Result.Height := ScaleY(25);
  Result.Caption := ACaption;
  Result.OnClick := AOnClick;
end;

procedure CreateWizardPages;
var
  t: TNewStaticText;
begin
  // --- страница 1: подключите принтер ---
  ConnPage := CreateCustomPage(wpWelcome, CustomMessage('ConnCaption'), CustomMessage('ConnSub'));
  t := TNewStaticText.Create(ConnPage);
  t.Parent := ConnPage.Surface;
  t.AutoSize := False;
  t.WordWrap := True;
  t.Left := 0;
  t.Top := 0;
  t.Width := ConnPage.SurfaceWidth;
  t.Height := ScaleY(96);
  t.Caption := CustomMessage('ConnText');
  ConnCheck := TNewCheckBox.Create(ConnPage);
  ConnCheck.Parent := ConnPage.Surface;
  ConnCheck.Left := 0;
  ConnCheck.Top := ScaleY(104);
  ConnCheck.Width := ConnPage.SurfaceWidth;
  ConnCheck.Caption := CustomMessage('ConnCheck');
  ConnCheck.OnClick := @ConnCheckClick;
  PaperCheck := TNewCheckBox.Create(ConnPage);
  PaperCheck.Parent := ConnPage.Surface;
  PaperCheck.Left := 0;
  PaperCheck.Top := ScaleY(128);
  PaperCheck.Width := ConnPage.SurfaceWidth;
  PaperCheck.Caption := CustomMessage('PaperCheck');
  PaperCheck.OnClick := @ConnCheckClick;

  // галочка учёта установки (у помощников скрыта: они отправляют всегда)
  StatsCheck := TNewCheckBox.Create(ConnPage);
  StatsCheck.Parent := ConnPage.Surface;
  StatsCheck.Left := 0;
  StatsCheck.Top := ScaleY(164);
  StatsCheck.Width := ConnPage.SurfaceWidth;
  StatsCheck.Caption := CustomMessage('StatsCheck');
  StatsCheck.Checked := True;
  StatsCheck.Visible := not HelperOn;
  StatsNote := TNewStaticText.Create(ConnPage);
  StatsNote.Parent := ConnPage.Surface;
  StatsNote.AutoSize := False;
  StatsNote.WordWrap := True;
  StatsNote.Left := ScaleX(18);
  StatsNote.Top := ScaleY(184);
  StatsNote.Width := ConnPage.SurfaceWidth - ScaleX(18);
  StatsNote.Height := ScaleY(50);
  StatsNote.Caption := CustomMessage('StatsNote');
  StatsNote.Visible := not HelperOn;

  // --- страница 2: поиск принтера ---
  DetPage := CreateCustomPage(ConnPage.ID, CustomMessage('DetCaption'), CustomMessage('DetSub'));
  DetMsg := TNewStaticText.Create(DetPage);
  DetMsg.Parent := DetPage.Surface;
  DetMsg.AutoSize := False;
  DetMsg.WordWrap := True;
  DetMsg.Left := 0;
  DetMsg.Top := 0;
  DetMsg.Width := DetPage.SurfaceWidth;
  DetMsg.Height := ScaleY(60);
  DetMsg.Font.Size := DetMsg.Font.Size + 1;

  BtnRetry := MakeButton(0, CustomMessage('BtnRetry'), @BtnRetryClick);

  DetWarn := TNewStaticText.Create(DetPage);
  DetWarn.Parent := DetPage.Surface;
  DetWarn.AutoSize := False;
  DetWarn.WordWrap := True;
  DetWarn.Left := 0;
  DetWarn.Width := DetPage.SurfaceWidth;
  DetWarn.Height := ScaleY(40);
  DetWarn.Top := DetPage.SurfaceHeight - DetWarn.Height;
  DetWarn.Font.Style := [fsBold];
  DetWarn.Font.Color := clRed;
  DetWarn.Anchors := [akLeft, akRight, akBottom];
end;

// ---------------------------------------------------------------------------
// Анимация на странице установки
// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// Логотип CAPT летает поверх мамонтов по диагонали и отскакивает от краёв, при каждом ударе меняя цвет (как заставка у DVD-плеера).
// Рисуется прямо в копию кадра: из логотипа заранее берутся только заметные пиксели (позиция + прозрачность), на каждом шаге
// они смешиваются с кадром. Если файл логотипа не загрузился - анимация идёт без него.
// ---------------------------------------------------------------------------
var
  Work: TBitmap;                              // кадр с логотипом
  LogoPX, LogoPY, LogoPA: array of Integer;   // x, y и непрозрачность (0..255) каждого пикселя логотипа
  LogoN, LogoW, LogoH: Integer;
  LogoX, LogoY, LogoDX, LogoDY, LogoCol: Integer;
  LogoTick: Integer;
  StageW, StageH: Integer;                    // размер области анимации в пикселях экрана

function GetWindowLong(hWnd: LongWord; nIndex: Integer): LongInt; external 'GetWindowLongW@user32.dll stdcall';
function SetWindowLong(hWnd: LongWord; nIndex: Integer; dwNewLong: LongInt): LongInt; external 'SetWindowLongW@user32.dll stdcall';
function SetStretchBltMode(hdc: LongWord; mode: Integer): Integer; external 'SetStretchBltMode@gdi32.dll stdcall';
function StretchBlt(hdcDest: LongWord; xDest, yDest, wDest, hDest: Integer; hdcSrc: LongWord; xSrc, ySrc, wSrc, hSrc: Integer; rop: LongWord): Integer; external 'StretchBlt@gdi32.dll stdcall';

procedure LoadLogo;
var
  b: TBitmap;
  x, y, a, n, s: Integer;
  nm: String;
begin
  LogoN := 0;
  // Рисуем сразу в размере экрана: размер области и логотипа берём под масштаб Windows (100/125/150/175/200%).
  StageW := ScaleX(300);
  StageH := ScaleY(120);
  s := ScaleX(100);
  if s < 112 then nm := 'capt_logo_100.bmp'
  else if s < 137 then nm := 'capt_logo_125.bmp'
  else if s < 162 then nm := 'capt_logo_150.bmp'
  else if s < 187 then nm := 'capt_logo_175.bmp'
  else nm := 'capt_logo_200.bmp';
  try
    ExtractTemporaryFile(nm);
    b := TBitmap.Create;
    try
      b.LoadFromFile(ExpandConstant('{tmp}\' + nm));
      LogoW := b.Width;
      LogoH := b.Height;
      SetArrayLength(LogoPX, LogoW * LogoH);
      SetArrayLength(LogoPY, LogoW * LogoH);
      SetArrayLength(LogoPA, LogoW * LogoH);
      n := 0;
      for y := 0 to LogoH - 1 do
        for x := 0 to LogoW - 1 do
        begin
          a := 255 - (b.Canvas.Pixels[x, y] and $FF);
          if a > 16 then
          begin
            LogoPX[n] := x;
            LogoPY[n] := y;
            LogoPA[n] := a;
            n := n + 1;
          end;
        end;
      LogoN := n;
    finally
      b.Free;
    end;
    Work := TBitmap.Create;
    Work.Width := StageW;
    Work.Height := StageH;
  except
    LogoN := 0;
  end;
  LogoX := ScaleX(20);
  LogoY := ScaleY(10);
  LogoDX := ScaleX(3);
  LogoDY := ScaleY(2);
  LogoCol := 0;
  LogoTick := 0;
end;

procedure LogoTint(var r, g, b: Integer);
begin
  case LogoCol of
    0: begin r := 20;  g := 20;  b := 20;  end;   // чёрный
    1: begin r := 220; g := 30;  b := 50;  end;   // красный
    2: begin r := 30;  g := 100; b := 220; end;   // синий
    3: begin r := 30;  g := 160; b := 60;  end;   // зелёный
    4: begin r := 240; g := 150; b := 20;  end;   // оранжевый
  else
    begin r := 150; g := 50; b := 200; end;       // фиолетовый
  end;
end;

procedure MoveLogo(areaW, areaH: Integer);
begin
  LogoX := LogoX + LogoDX;
  LogoY := LogoY + LogoDY;
  if LogoX <= 0 then
  begin
    LogoX := 0;
    if LogoDX < 0 then LogoDX := -LogoDX;
    LogoCol := (LogoCol + 1) mod 6;
  end
  else if LogoX >= areaW - LogoW then
  begin
    LogoX := areaW - LogoW;
    if LogoDX > 0 then LogoDX := -LogoDX;
    LogoCol := (LogoCol + 1) mod 6;
  end;
  if LogoY <= 0 then
  begin
    LogoY := 0;
    if LogoDY < 0 then LogoDY := -LogoDY;
    LogoCol := (LogoCol + 1) mod 6;
  end
  else if LogoY >= areaH - LogoH then
  begin
    LogoY := areaH - LogoH;
    if LogoDY > 0 then LogoDY := -LogoDY;
    LogoCol := (LogoCol + 1) mod 6;
  end;
end;

procedure DrawLogoOn(bmp: TBitmap);
var
  k, px, py, c, r, g, b, a, tr, tg, tb: Integer;
begin
  LogoTint(tr, tg, tb);
  for k := 0 to LogoN - 1 do
  begin
    px := LogoX + LogoPX[k];
    py := LogoY + LogoPY[k];
    if (px >= 0) and (px < bmp.Width) and (py >= 0) and (py < bmp.Height) then
    begin
      c := bmp.Canvas.Pixels[px, py];
      a := LogoPA[k];
      r := ((c and $FF) * (255 - a) + tr * a) div 255;
      g := (((c shr 8) and $FF) * (255 - a) + tg * a) div 255;
      b := (((c shr 16) and $FF) * (255 - a) + tb * a) div 255;
      bmp.Canvas.Pixels[px, py] := r + (g shl 8) + (b shl 16);
    end;
  end;
end;

procedure CreateAnimation;
var
  i, d: Integer;
  nm: String;
begin
  for i := 0 to 11 do
  begin
    nm := 'f' + IntToStr(i + 1) + '.bmp';
    ExtractTemporaryFile(nm);
    Frames[i] := TBitmap.Create;
    Frames[i].LoadFromFile(ExpandConstant('{tmp}\' + nm));
  end;
  LoadLogo;
  d := ScaleY(120) + ScaleY(16);
  with WizardForm do
  begin
    AnimImg := TBitmapImage.Create(WizardForm);
    AnimImg.Parent := InstallingPage;
    AnimImg.AutoSize := False;
    AnimImg.Stretch := True;   // кадры 300x120 px фиксированы, а рамка масштабируется по DPI экрана (125% = 375x150): без растяжения справа и снизу оставалась серая область
    AnimImg.Width := ScaleX(300);
    AnimImg.Height := ScaleY(120);
    AnimImg.Left := (InstallingPage.ClientWidth - AnimImg.Width) div 2;
    AnimImg.Top := StatusLabel.Top;
    AnimImg.Bitmap.Assign(Frames[0]);
    // всё остальное сдвигаем вниз: картинка оказывается над полосой
    StatusLabel.Top := StatusLabel.Top + d;
    StatusLabel.AutoSize := False;
    StatusLabel.WordWrap := True;
    StatusLabel.Width := InstallingPage.ClientWidth;
    StatusLabel.Height := ScaleY(48);   // три строки: этап (иногда в две строки) и "процент - прошло м:сс"
    // надпись хода установки меняется раз в секунду и заставляет перерисовывать страницу - без двойной буферизации мамонты моргали.
    // DoubleBuffered в Inno недоступен: включаем WS_EX_COMPOSITED (рисование страницы целиком в памяти) через user32.
    SetWindowLong(InstallingPage.Handle, -20, GetWindowLong(InstallingPage.Handle, -20) or $02000000);
    FileNameLabel.Top := FileNameLabel.Top + d + ScaleY(34);
    ProgressGauge.Top := ProgressGauge.Top + d + ScaleY(34);
  end;
  LastFrame := 0;
end;

procedure ShowFrame(f: Integer);
begin
  LastFrame := f;
  if LogoN > 0 then
  begin
    try
      // кадр мамонтов растягивается под размер экрана (StretchBlt из GDI, как делает TBitmapImage), затем логотип поверх
      SetStretchBltMode(Work.Canvas.Handle, 3);   // COLORONCOLOR: пиксельная графика без размытия
      if StretchBlt(Work.Canvas.Handle, 0, 0, StageW, StageH, Frames[f].Canvas.Handle, 0, 0, Frames[f].Width, Frames[f].Height, $00CC0020) = 0 then
        RaiseException('StretchBlt failed');   // уйдёт в except ниже: логотип отключится, мамонты останутся
      DrawLogoOn(Work);
      AnimImg.Bitmap.Assign(Work);
    except
      LogoN := 0;   // логотип - украшение: при любой ошибке отключаем его, мамонты продолжают идти
      AnimImg.Bitmap.Assign(Frames[f]);
    end;
  end
  else
    AnimImg.Bitmap.Assign(Frames[f]);
end;

function GetTickCount: LongWord; external 'GetTickCount@kernel32.dll stdcall';

var
  ScriptRunning: Boolean;      // идёт setup.ps1: на полосе его ход
  ScriptStartTick: LongWord;
  ScriptPct: Integer;

// Ход setup.ps1: скрипт пишет в {app}\progress.txt ключ текущего этапа, мастер переводит его в процент, название этапа и
// прошедшее время. Оставшееся время не показываем: оно зависит от интернета и от того, как быстро пройдут окно Ghostscript.
procedure UpdateScriptProgress;
var
  s: AnsiString;
  key, txt: String;
  pct, secs: Integer;
begin
  key := '';
  if LoadStringFromFile(ExpandConstant('{app}\progress.txt'), s) then key := Lowercase(Trim(String(s)));
  pct := 5;
  txt := CustomMessage('ProgDetect');
  if key = 'copy' then begin pct := 10; txt := CustomMessage('ProgCopy'); end
  else if key = 'gs' then begin pct := 20; txt := CustomMessage('ProgGs'); end
  else if key = 'redmon' then begin pct := 50; txt := CustomMessage('ProgRedmon'); end
  else if key = 'driver' then begin pct := 60; txt := CustomMessage('ProgDriver'); end
  else if key = 'queue' then begin pct := 75; txt := CustomMessage('ProgQueue'); end
  else if key = 'ppd' then begin pct := 88; txt := CustomMessage('ProgPpd'); end
  else if key = 'done' then begin pct := 100; txt := CustomMessage('ProgDone'); end;
  if pct < ScriptPct then pct := ScriptPct;   // полоса не идёт назад
  ScriptPct := pct;
  secs := (GetTickCount - ScriptStartTick) div 1000;
  WizardForm.ProgressGauge.Position := pct;
  WizardForm.StatusLabel.Caption := txt + #13#10 + IntToStr(pct) + '% - ' + CustomMessage('ProgElapsed') + ' ' +
    IntToStr(secs div 60) + ':' + Format('%.2d', [secs mod 60]);
end;

// Таймер (75 мс): логотип двигается каждый шаг, кадр мамонтов меняется через шаг (как раньше, раз в 150 мс), а раз в ~1 с
// обновляется полоса хода setup.ps1. Крутится, пока идёт установка.
procedure AnimTimerProc(h, msg, id, t: LongWord);
var
  f: Integer;
begin
  LogoTick := LogoTick + 1;
  if ScriptRunning and ((LogoTick mod 13) = 0) then UpdateScriptProgress;
  if LogoN > 0 then MoveLogo(StageW, StageH);
  f := LastFrame;
  if (LogoTick mod 2) = 0 then f := (LastFrame + 1) mod 12;
  ShowFrame(f);
end;

procedure StartAnimTimer;
begin
  if TimerId = 0 then
    TimerId := SetTimer(0, 0, 75, CreateCallback(@AnimTimerProc));
end;

procedure StopAnimTimer;
begin
  if PollId <> 0 then
  begin
    KillTimer(0, PollId);
    PollId := 0;
  end;
  if TimerId <> 0 then
  begin
    KillTimer(0, TimerId);
    TimerId := 0;
  end;
end;

procedure ExitProcess(uExitCode: Integer); external 'ExitProcess@kernel32.dll stdcall';

var
  InstallRc: Integer;        // код выхода setup.ps1 (0 = успех)
  InstallFailed: Boolean;

// Запуск setup.ps1 скрытно, вывод пишется в install_output.log. Install.cmd не используем: в конце у него pause.
procedure RunSetupScript;
var
  p, pre: String;
  rc: Integer;
begin
  // -NoTest: пробную страницу печатает отдельный шаг с галочкой на последней странице (см. [Run] postinstall).
  p := 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "' + ExpandConstant('{app}') + '\setup.ps1" -Lang ' +
       CustomMessage('UninstLang') + ' -Models "' + ModelsParam('') + '" -NoTest ' + StatsParams('');
  if WizardSilent then p := p + ' -Silent';
  // Без chcp 65001: вывод встроенных программ Windows должен читаться PowerShell в родной кодировке, а в UTF-8 его журнал
  // (install_output.log) пишет сам setup.ps1 через Start-Transcript. Перенаправление cmd (install_cmd.log) - только запасное.
  pre := '';
  // полоса: дальше её ведёт ход setup.ps1 (UpdateScriptProgress), а не копирование файлов, которое уже закончилось
  DeleteFile(ExpandConstant('{app}\progress.txt'));
  WizardForm.ProgressGauge.Min := 0;
  WizardForm.ProgressGauge.Max := 100;
  ScriptPct := 0;
  ScriptStartTick := GetTickCount;
  ScriptRunning := True;
  UpdateScriptProgress;
  // Мастер 32-разрядный: обычный {cmd} дал бы 32-разрядные cmd и powershell, которые не видят pnputil и др. из System32.
  // Секция [Run] в 64-разрядном режиме этого не делала. {sysnative} = настоящая 64-разрядная System32 (Windows 8.1+ x64).
  if not Exec(ExpandConstant('{sysnative}\cmd.exe'), '/c ' + pre + p + ' > "' + ExpandConstant('{app}') + '\install_cmd.log" 2>&1',
              ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, rc) then rc := 1;
  ScriptRunning := False;
  if rc = 0 then WizardForm.ProgressGauge.Position := 100;
  InstallRc := rc;
  InstallFailed := (rc <> 0);
end;

// Для Check: у [Run] с галочкой "Напечатать тестовую страницу" (показывается только при успешной установке).
function InstallSucceeded: Boolean;
begin
  Result := not InstallFailed;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then StartAnimTimer
  else if CurStep = ssPostInstall then RunSetupScript
  else if CurStep = ssDone then StopAnimTimer;
end;

// Кадры мамонтов раньше перелистывались ещё и по ходу копирования файлов - вместе с таймером они на копировании бежали
// быстрее. Теперь скорость задаёт только таймер (AnimTimerProc), обработчик хода копирования не нужен.

// ---------------------------------------------------------------------------
procedure InitializeWizard;
begin
  InitModels;
  InitStats;
  CreateWizardPages;
  CreateAnimation;
  PollId := SetTimer(0, 0, 2000, CreateCallback(@PollTimerProc));
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = ConnPage.ID then
    WizardForm.NextButton.Enabled := ConnCheck.Checked and PaperCheck.Checked
  else if CurPageID = DetPage.ID then
    RunDetection
  else if CurPageID = wpFinished then
  begin
    StopAnimTimer;
    if InstallFailed then
    begin
      // Честный итог: не "Установка завершена", а причина и путь к журналу.
      WizardForm.FinishedHeadingLabel.Caption := CustomMessage('FailHeading');
      WizardForm.FinishedLabel.Height := WizardForm.FinishedLabel.Height + ScaleY(60);   // поле по умолчанию короткое: путь к журналу обрезался
      case InstallRc of
        10: WizardForm.FinishedLabel.Caption := FmtMessage(CustomMessage('FailText'), [CustomMessage('FailGs'), ExpandConstant('{app}') + '\install_output.log']);
        11: WizardForm.FinishedLabel.Caption := FmtMessage(CustomMessage('FailText'), [CustomMessage('FailRm'), ExpandConstant('{app}') + '\install_output.log']);
        12: WizardForm.FinishedLabel.Caption := FmtMessage(CustomMessage('FailText'), [CustomMessage('FailWpp'), ExpandConstant('{app}') + '\install_output.log']);
      else
        WizardForm.FinishedLabel.Caption := FmtMessage(CustomMessage('FailText'), [CustomMessage('FailGeneric'), ExpandConstant('{app}') + '\install_output.log']);
      end;
    end;
  end;
end;

procedure DeinitializeSetup;
var
  i: Integer;
begin
  StopAnimTimer;
  for i := 0 to 11 do
    if Frames[i] <> nil then Frames[i].Free;
  // Тихая установка: код выхода мастера = код выхода setup.ps1, чтобы скрипты и помощники видели неудачу.
  if InstallFailed and WizardSilent then ExitProcess(InstallRc);
end;

// Страница "Готово к установке": какие принтеры ставим и что предупредить заранее. Установщик Ghostscript с версии 10.01
// не поддерживает тихую установку (/S), поэтому его окно придётся пройти вручную - говорим об этом до начала.
function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo, MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
var
  i: Integer;
begin
  Result := CustomMessage('MemoPrinters') + NewLine;
  for i := 0 to GetArrayLength(Models) - 1 do
    if Selected[i] then
      Result := Result + Space + Models[i].Name + NewLine;
  if not GsInstalled then
    Result := Result + NewLine + CustomMessage('GsNote') + NewLine;
  // Redmon ставится молча (setup64.exe /S), предупреждать о его окне больше не нужно. Защищённый режим печати - заранее:
  // setup.ps1 с ним всё равно остановится (код 12), но человек узнает об этом до установки.
  if WppEnabled then
    Result := Result + NewLine + CustomMessage('WppNote') + NewLine;
  if not HelperOn then
  begin
    if StatsParams('') = '' then
      Result := Result + NewLine + CustomMessage('StatsMemoOn') + NewLine
    else
      Result := Result + NewLine + CustomMessage('StatsMemoOff') + NewLine;
  end;
end;
