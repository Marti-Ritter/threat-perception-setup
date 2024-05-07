src = getselectedsource(vidobj);
src.LineSelector='Line3';
src.TriggerMode='On';
triggerconfig(vidobj, 'hardware');
file = VideoWriter('C:\Users\Larkum_Practical_06\Bpod Local\Data\FakeSubject\Airpuff_new\Session Data\tonto7','Motion JPEG 2000');
% file.Quality = 40;
% file.VideoFormat='Grayscale';
file.CompressionRatio = 90;
% file.MJ2BitDepth=8;
vidobj.FramesAcquiredFcn = @getDepthMetadata;
vidobj.DiskLogger = file;
vidobj.FramesPerTrigger = 3000;
start(vidobj)
sma = NewStateMachine();
sma = SetGlobalTimer(sma, 'TimerID', 1, 'Duration', 0.001, 'OnsetDelay', 0,...
                     'Channel', 'BNC1', 'OnsetMessage', 1,'OffMessage', 0,...
                     'Loop', 1, 'SendGlobalTimerEvents', 0, 'LoopInterval', 0.01); 
sma = AddState(sma, 'Name', 'TimerTrig1', ...
    'Timer', 0,...
    'StateChangeConditions', {'Tup', 'WaitForPoke'},...
    'OutputActions', {'GlobalTimerTrig', 1});
sma = AddState(sma, 'Name', 'WaitForPoke', ...
    'Timer', 4,...
    'StateChangeConditions', {'Tup', 'WaitForPoke2'},...
    'OutputActions', {});
sma = AddState(sma, 'Name', 'WaitForPoke2', ...
    'Timer', 1,...
    'StateChangeConditions', {'Tup', 'StopGlobalTimer'},...
    'OutputActions', {});
sma = AddState(sma, 'Name', 'StopGlobalTimer', ...
    'Timer', 0,...
    'StateChangeConditions', {'Tup', 'exit'},...
    'OutputActions', {'GlobalTimerCancel', 1});
SendStateMatrix(sma); % Send state machine to the Bpod state machine device
RawEvents = RunStateMatrix;
vidobj.FramesAcquiredFcnCount = vidobj.FramesAcquired;
while vidobj.FramesAcquired ~= vidobj.DiskLoggerFrameCount
    wait(0.1)
end
disp('lol')
% Run the trial and return events
stop(vidobj)
%[data time]=getdata(vidobj, vidobj.FramesAcquired);


%%
vidobj = videoinput('gentl', 2);



sma = NewStateMachine();
sma = AddState(sma, 'Name', 'WaitForPoke', ...
    'Timer', 4,...
    'StateChangeConditions', {'Tup', 'exit'},...
    'OutputActions', {});
sma = EditState(sma,'WaitForPoke', ...
    'Timer', 8);


SendStateMatrix(sma); % Send state machine to the Bpod state machine device
RawEvents = RunStateMatrix;