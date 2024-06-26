function TPM
global BpodSystem
global PCSocket
global CurrentTrial

%% Setup (runs once before the first trial and stops the code until user continues)
MaxTrials = 1000; % Set to some sane value, for preallocation

%--- Define parameters and trial structure
S = BpodSystem.ProtocolSettings; % Load settings chosen in launch manager into current workspace as a struct called S
if isempty(fieldnames(S))  % If settings file was an empty struct, populate struct with default settings
    S.GUI.TrialLength = 1; % how long does the trial last
    S.GUI.LickWait = 2; % how much time has the mouse to lick on the spout
    S.GUI.RewardWait = 2; % how much time has the mouse to consume the reward
    S.GUI.RewardAmount = 5; %ul
    
    TypeNames = {'Blocked', 'Visual', 'Smell', 'Open', 'Random'};
    S.GUI.TypeSelector = 1;
    S.GUIMeta.TypeSelector.Style = 'popupmenu';        % This dropdown-menu shows all available Types, which are contained in a list.
    S.GUIMeta.TypeSelector.String = TypeNames;       % Whatever is selected here will determine the TrialType to use for the next trial.
    S.GUI.BlockedProb = 0.25;
    S.GUI.VisualProb = 0.25;
    S.GUI.SmellProb = 0.25;
    S.GUI.OpenProb = 0.25;
    S.GUIPanels.TrialTypes = {'TypeSelector', 'BlockedProb', 'VisualProb', 'SmellProb', 'OpenProb'}; % UI panel for TrialType parameters
end

%% Define serial messages being sent to modules
LoadSerialMessages('AnalogIn1', {['L' 1], ['L' 0]});
% AnalogIn1:
% command 1: start logging,
% command 2: stop logging

%% Define serial messages being sent to modules
BpodSystem.SoftCodeHandlerFunction = 'SoftCodeHandler';

%% Define trials
% 1: Blocked, 2: Visual, 3: Smell, 4: Open
% Normalizing all probabilities, if someone enters a high number, and
% calculating the corresponding frequency
ProbList = [S.GUI.BlockedProb, S.GUI.VisualProb, S.GUI.SmellProb, S.GUI.OpenProb];
% Calculate the frequency of each state from the relative probability and
% the number of Trials, then calculate the raw TrialTypes vector by
% repeating the index of a trial type the required number of trials.
TrialTypes = [];
for i = 1:length(ProbList)
   Frequency = round((ProbList(i) / sum(ProbList)) * MaxTrials);
   TrialTypes = [TrialTypes, repmat([i], 1, Frequency)];
end
% If a single trialtype gets lost due to rounding, add a blocking state to
% the front.
if length(TrialTypes) < MaxTrials
    TrialTypes = [[1], TrialTypes];
end
% Shuffle everything
TrialTypes = TrialTypes(randperm(length(TrialTypes)));
BpodSystem.Data.TrialTypes = []; % The trial type of each trial completed will be added here.


OldProbs = ProbList; % Remembering this allows us to redraw the projected trials on the fly.
%% Initialize plots
BpodSystem.ProtocolFigures.OutcomePlotFig = figure('Position', [50 540 1000 250],'name','Outcome plot','numbertitle','off', 'MenuBar', 'none', 'Resize', 'off');
BpodSystem.GUIHandles.OutcomePlot = axes('Position', [.075 .3 .89 .6]);
TrialTypeOutcomePlot(BpodSystem.GUIHandles.OutcomePlot,'init',TrialTypes);
BpodNotebook('init'); % Initialize Bpod notebook (for manual data annotation)
BpodParameterGUI('init', S); % Initialize parameter GUI plugin

%% Set up Python environment
pyExec = 'D:\Users\TPM\Anaconda3\envs\TPM\pythonw.exe';
pyRoot = fileparts(pyExec);
p = getenv('PATH');
p = strsplit(p, ';');
addToPath = {
    pyRoot
    fullfile(pyRoot, 'Library', 'mingw-w64', 'bin')
    fullfile(pyRoot, 'Library', 'usr', 'bin')
    fullfile(pyRoot, 'Library', 'bin')
    fullfile(pyRoot, 'Scripts')
    fullfile(pyRoot, 'bin')
    };
p = [addToPath(:); p(:)];
p = unique(p, 'stable');
p = strjoin(p, ';');
setenv('PATH', p);

%% Prepare communication with other elements
PCSocket = tcpip('localhost', 30000, 'NetworkRole', 'server', 'Timeout', inf);
% system('"D:\Users\TPM\Anaconda3\envs\TPM\pythonw.exe" "D:\gin\TPM\30_code\PC\PC_Recording.py" &');
fopen(PCSocket);
fread(PCSocket,1);
disp('Recorders connected, confirmation byte received.')

ModuleWrite('RaspbPi1', 4);
disp('Raspberry Pi told to start screen.')

%% Main trial loop
for CurrentTrial = 1:MaxTrials    
    S = BpodParameterGUI('sync', S); % Sync parameters with BpodParameterGUI plugin
    R = GetValveTimes(S.GUI.RewardAmount, [1]); ValveTime = R(1); % Update reward amount

    SoftCodeHandler('SetLocation');

    %--- Typically, a block of code here will compute variables for assembling this trial's state machine
    ProbList = [S.GUI.BlockedProb, S.GUI.VisualProb, S.GUI.SmellProb, S.GUI.OpenProb];
    if ~isequal(OldProbs, ProbList) % Check if someone changed the Probs
        OldProbs = ProbList;
        disp('Probs were adjusted.')
        NewTrialTypes = [];
        RemainingTrials = MaxTrials - CurrentTrial;
        for i=1:length(ProbList)
           Frequency = round((ProbList(i) / sum(ProbList)) * RemainingTrials);
           NewTrialTypes = [NewTrialTypes, repmat([i], 1, Frequency)];
        end
        NewTrialTypes = [NewTrialTypes, [1]];
        NewTrialTypes = NewTrialTypes(1:RemainingTrials);
        
        if length(NewTrialTypes) < RemainingTrials
            NewTrialTypes = [[1], NewTrialTypes];
        end
        disp(length(NewTrialTypes))
        disp(RemainingTrials)

        NewTrialTypes = NewTrialTypes(randperm(length(NewTrialTypes)));
        TrialTypes(CurrentTrial+1:MaxTrials) = NewTrialTypes;
    end
    if S.GUI.TypeSelector ~= 5
        TrialTypes(CurrentTrial) = S.GUI.TypeSelector;
    end
    if CurrentTrial ~= 1
        TrialTypeOutcomePlot(BpodSystem.GUIHandles.OutcomePlot,'update',BpodSystem.Data.nTrials+1,TrialTypes,Outcomes); % Update the Plot
    else
        TrialTypeOutcomePlot(BpodSystem.GUIHandles.OutcomePlot,'update',CurrentTrial,TrialTypes,[0]); % Update the Plot
    end
        
    %--- Writing the disk state to the Raspberry Pi
    ModuleWrite('RaspbPi1', TrialTypes(CurrentTrial) - 1 + 30);

    sma = NewStateMachine(); % Initialize new state machine description
    sma = SetGlobalTimer(sma, 'TimerID', 1, 'Duration', 0.001, 'OnsetDelay', 0,...
                     'Channel', 'BNC1', 'OnsetMessage', 1,'OffMessage', 0,...
                     'Loop', 1, 'SendGlobalTimerEvents', 0, 'LoopInterval', 0.01); 
    sma = AddState(sma, 'Name', 'S0', ...
        'Timer', 0,...
        'StateChangeConditions', {'Tup', 'S1'},...
        'OutputActions', {'SoftCode', 1, 'RaspbPi1', 1, 'AnalogIn1', 1, 'GlobalTimerTrig', 1}); 
    sma = AddState(sma, 'Name', 'S1', ...
        'Timer', S.GUI.TrialLength,...
        'StateChangeConditions', {'RaspbPi1_1', 'S2', 'Tup', 'S6'},...
        'OutputActions', {}); 
    sma = AddState(sma, 'Name', 'S2', ...
        'Timer', S.GUI.LickWait,...
        'StateChangeConditions', {'Port1In', 'S3', 'Tup', 'S7', 'RaspbPi1_2', 'S8'},...
        'OutputActions', {});
    sma = AddState(sma, 'Name', 'S3', ...
        'Timer', ValveTime,...
        'StateChangeConditions', {'Tup', 'S4'},...
        'OutputActions', {'Valve1', true});
    sma = AddState(sma, 'Name', 'S4', ...
        'Timer', S.GUI.RewardWait,...
        'StateChangeConditions', {'Tup', 'S5', 'RaspbPi1_2', 'S8'},...
        'OutputActions', {}); 
    sma = AddState(sma, 'Name', 'S5', ...
        'Timer', 0,...
        'StateChangeConditions', {'Tup', 'exit'},...
        'OutputActions', {'SoftCode', 2, 'RaspbPi1', 2, 'AnalogIn1', 2, 'GlobalTimerCancel', 1});
    sma = AddState(sma, 'Name', 'S6', ...
        'Timer', 0,...
        'StateChangeConditions', {'Tup', 'exit'},...
        'OutputActions', {'SoftCode', 2, 'RaspbPi1', 2, 'AnalogIn1', 2, 'GlobalTimerCancel', 1});
    sma = AddState(sma, 'Name', 'S7', ...
        'Timer', 0,...
        'StateChangeConditions', {'Tup', 'exit'},...
        'OutputActions', {'SoftCode', 2, 'RaspbPi1', 2, 'AnalogIn1', 2, 'GlobalTimerCancel', 1}); 
    sma = AddState(sma, 'Name', 'S8', ...
        'Timer', 0,...
        'StateChangeConditions', {'Tup', 'exit'},...
        'OutputActions', {'SoftCode', 2, 'RaspbPi1', 2, 'AnalogIn1', 2,'GlobalTimerCancel', 1}); 

    SendStateMatrix(sma); % Send state machine to the Bpod state machine device
    RawEvents = RunStateMatrix; % Run the trial and return events
    
    %--- Tell the recorders to save their files
    SoftCodeHandler(3);
    % Wait for the confirmation byte that the saving was finished.
    fread(PCSocket,1);

    %--- Package and save the trial's data, update plots
    if ~isempty(fieldnames(RawEvents)) % If trial data was returned
        BpodSystem.Data = AddTrialEvents(BpodSystem.Data,RawEvents); % Computes trial events from raw data
        BpodSystem.Data = BpodNotebook('sync', BpodSystem.Data); % Sync with Bpod notebook plugin
        BpodSystem.Data.TrialSettings(CurrentTrial) = S; % Adds the settings used for the current trial to the Data struct (to be saved after the trial ends)
        BpodSystem.Data.TrialTypes(CurrentTrial) = TrialTypes(CurrentTrial); % Adds the trial type of the current trial to data
        SaveBpodSessionData; % Saves the field BpodSystem.Data to the current data file
        
        %--- Typically a block of code here will update online plots using the newly updated BpodSystem.Data
        Outcomes = zeros(1,BpodSystem.Data.nTrials);
        for x = 1:BpodSystem.Data.nTrials
            if ~isnan(BpodSystem.Data.RawEvents.Trial{x}.States.S5(1))
                Outcomes(x) = 1;
            elseif ~isnan(BpodSystem.Data.RawEvents.Trial{x}.States.S8(1))
                Outcomes(x) = 0;
            elseif ~isnan(BpodSystem.Data.RawEvents.Trial{x}.States.S7(1))
                Outcomes(x) = 2;
            else  % S6
                Outcomes(x) = 3;
            end
        end
    % TrialTypeOutcomePlot(BpodSystem.GUIHandles.OutcomePlot,'update',BpodSystem.Data.nTrials+1,TrialTypes,Outcomes);
    end
    
    %--- This final block of code is necessary for the Bpod console's pause and stop buttons to work
    HandlePauseCondition; % Checks to see if the protocol is paused. If so, waits until user resumes.
    if BpodSystem.Status.BeingUsed == 0
        CleanUp
        return
    end
end
%--- Here we clear all remaining elements before the protocol ends
CleanUp
end

function CleanUp
    global PCSocket
    SoftCodeHandler(4);
    disp('Python processes have shut down.');
    % Wait for the confirmation byte that the shutting down was finished.
    fread(PCSocket,1);
    ModuleWrite('RaspbPi1', 5);
    disp('Raspberry Pi told to shut down screen.');
end
