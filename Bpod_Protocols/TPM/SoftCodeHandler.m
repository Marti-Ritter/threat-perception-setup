function SoftCodeHandler(Byte)
global BpodSystem
global PCSocket
global CurrentTrial

switch Byte
    case 'SetLocation'
        s = BpodSystem.Path.CurrentDataFile;
        s1 = strsplit(s, '.');
        s2 = strsplit(s1{1,1}, '\');
        data = join(["set_location ", s1{1,1}, '\Trial', CurrentTrial,'\', s2{end}, '_Trial', CurrentTrial, '|'], '');
        fwrite(PCSocket, data);
    case 1
        data = '1|';
        fwrite(PCSocket, data);
    case 2
        data = '2|';
        fwrite(PCSocket, data);
    case 3
        data = '3|';
        fwrite(PCSocket, data);
    case 4
        data = '4|';
        fwrite(PCSocket, data);
end