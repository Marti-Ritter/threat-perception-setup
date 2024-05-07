global PCSocket
PCSocket = tcpip('localhost', 30000, 'NetworkRole', 'server', 'Timeout', inf);
% system('"D:\gin\TPM\30_code\venv\Scripts\pythonw.exe" "D:\gin\TPM\30_code\PC\PC_Recording.py" &');
fopen(PCSocket);
disp('connected')
disp(fread(PCSocket,1));
SoftCodeHandler(0)
SoftCodeHandler(1);
pause(2)
SoftCodeHandler(2);
SoftCodeHandler(3);
disp(fread(PCSocket,1));
SoftCodeHandler(4);
disp(fread(PCSocket,1));
