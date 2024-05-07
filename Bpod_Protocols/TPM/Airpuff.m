function Airpuff         
global BpodSystem

%% Setup (runs once before the first trial and stops the code until user continues)
MaxTrials = 1000; % Set to some sane value, for preallocation
BiasAdjustmentSteps = 5; % Set after how many trials the bias gets recalculated
SignalNames = {'Pulse 20Hz', 'Standing', 'Sine 20Hz'};
% This is a list of all available signals for the LED.
% They need to be defined in the same order as named here, otherwise the
% dropdown list wont link to the right ones.
RangeVoltage = 5;   % The range in which the cues will be played, like this
                    % -RangeVoltage:RangeVoltage.
                    % Important in case an amplifier is used, which takes
                    % different input ranges.

CamTrigger = false; % WIP: A flag which sets whether a trigger for a cam is
                    % played with a second WavePlayer. If this is set to
                    % true and no second WavePlayer is connected, the
                    % protocol will stop with an error.
                    
%--- Define parameters and trial structure
S = BpodSystem.ProtocolSettings; % Loads settings file chosen in launch manager into current workspace as a struct called 'S'
if isempty(fieldnames(S))  % If chosen settings file was an empty struct, populate struct with default settings
    % Define default settings here as fields of S (i.e S.InitialDelay = 3.2)
    % Note: Any parameters in S.GUI will be shown in UI edit boxes. Only
    % numerical values are supported in regular edit fields (not listboxes
    % or checkboxes).
    % See ParameterGUI plugin documentation to show parameters as other UI types (listboxes, checkboxes, buttons, text)

    S.GUI.AutoReward = 0; % Whether the mouse will be automatically rewarded (pairing).
    S.GUIMeta.AutoReward.Style = 'checkbox'; % Turn the previous setting into a checkbox
    S.GUI.RewardAmount = 5; % In ul.
    S.GUI.RewardDuration = 0; % In s. Only gets updated by the above value and, since there is no function to get reward from the valvetime, wont change anything if altered manually.
    S.GUIPanels.Reward = {'AutoReward', 'RewardAmount', 'RewardDuration'}; % UI panel for reward parameters

    S.GUI.AutomatedReaching = 1; % At 0 the reaching task has to be enabled manually, at 1 it will switch on or off on its own.
    S.GUIMeta.AutomatedReaching.Style = 'checkbox'; % Turn the previous setting into a checkbox
    S.GUI.ReachingTask = 0; % At 0 the reaching task is disabled, the mouse only has to lick. At 1 the mouse has to reach to get the reward.
    S.GUIMeta.ReachingTask.Style = 'checkbox'; % Turn the previous setting into a checkbox
    S.GUI.ReachingTaskBlockSize = 30; % At 0 only left trials, at 1 only right trials, 0.5 results in a uniform distribution
    S.GUIPanels.Reaching = {'AutomatedReaching', 'ReachingTask', 'ReachingTaskBlockSize'}; % UI panel for reaching task distribution parameters

    S.GUI.InitialDelay = 2; % Initial Delay, no licks allowed
    S.GUI.PuffLength = 2; % Duration of the airpuff
    S.GUI.DelayPeriodMean = 2; % Mean of the delay until licking is allowed, after the starting sound has played.
    S.GUI.DelayPeriodRange = 0.5; % Range in which the delay is random.
    S.GUI.ResponsePeriod = 2; % How much time has the mouse to lick? In autoreward-mode the blind AutoRewardPeriod shares the same length.
    S.GUIPanels.Timing = {'InitialDelay', 'PuffLength', 'DelayPeriodMean', 'DelayPeriodRange', 'ResponsePeriod'}; % UI panel for timing parameters

    S.GUI.Bias = 0.5; % At 0 only left trials, at 1 only right trials, 0.5 results in a uniform distribution
    S.GUI.BiasAutoAdjust = 1; % At 0 the bias is frozen and only changes with manual entries, at 1 it is recalculated every BiasAdjustmentSteps.
    S.GUIMeta.BiasAutoAdjust.Style = 'checkbox'; % Turn the previous setting into a checkbox
    S.GUIPanels.Distribution = {'Bias', 'BiasAutoAdjust'}; % UI panel for trialtype distribution parameters

    S.GUI.IlluminationProbability = 0.25; % Probability that one of the three listed phases runs with an activated LED
    S.GUI.AirpuffLED = 1;                           % This variable and the next 2 control the activation of
    S.GUIMeta.AirpuffLED.Style = 'checkbox';        % the LED during the respective phase. If the probability
    S.GUI.DelayPeriodLED = 1;                       % fires, one of the three is chosen randomly and adapts 
    S.GUIMeta.DelayPeriodLED.Style = 'checkbox';    % the respective phase to use an LED.
    S.GUI.ResponsePeriodLED = 1;
    S.GUIMeta.ResponsePeriodLED.Style = 'checkbox';
    S.GUI.LEDSignal = 1;
    S.GUIMeta.LEDSignal.Style = 'popupmenu';        % This dropdown-menu shows all available SignalNames, which are contained in a list.
    S.GUIMeta.LEDSignal.String = SignalNames;       % Whatever is selected here will be played over channel 2 of the WavePlayer.
    S.GUIPanels.Illumination = {'IlluminationProbability', 'AirpuffLED', 'DelayPeriodLED', 'ResponsePeriodLED', 'LEDSignal'}; % UI panel for illumination parameters

    S.GUI.ReachingDelay = 3; % How long has the micromanipulator to change configurations?
    S.GUI.FailureLength = 1; % How long does the failure phase last?
    S.GUI.InterTrialInterval = 2; % Duration of the period between trials.
    S.GUI.InterTrialIntervalFailure = 1; % Duration of the period before the new trial begins if the previous one failed.
    S.GUIPanels.Utility = {'ReachingDelay', 'FailureLength', 'InterTrialInterval', 'InterTrialIntervalFailure'}; % UI panel for utility (rarely used) parameters
end
BpodParameterGUI('init', S); % Initialize parameter GUI plugin
BpodParameterGUI('sync', S); % Initialize parameter GUI plugin
%% Define waveplayer-object and load waveforms for cues
W = BpodWavePlayer('COM3');
W.OutputRange = strcat('-', num2str(RangeVoltage), 'V:', num2str(RangeVoltage), 'V'); % OutputRange is set to fit the given VoltageRange.
[y,Fs] = audioread('C:\Windows\Media\ringout.wav'); % 'Failure' cue
W.SamplingRate = Fs; % Setting sampling rate to the rate from the wav.-file
myWave = (y(:,2) + y(:,1))/2; % Since the file has 2 lines, for 2 speakers, the mean is used for 1 speaker
myWave = myWave * min(RangeVoltage / max(myWave), -RangeVoltage / min(myWave)); % Stretching the wave to fit to -12V:12V
W.loadWaveform(1, myWave);
[y,Fs] = audioread('C:\Windows\Media\Windows Ding.wav'); % 'Go' cue
myWave = (y(:,2) + y(:,1))/2;
myWave = myWave * min(RangeVoltage / max(myWave), -RangeVoltage / min(myWave));
W.loadWaveform(2, myWave);

%% Define and load waveforms for LED (channel 2)
myMat = [5 * ones(1, round((1 / 20) * (2 / 50) * W.SamplingRate)), zeros(1, round((1 / 20) * (48 / 50) * W.SamplingRate))]; % A single pulse of 2ms 5V and 48ms 0V
Pulse20Hz = repmat(myMat, 1, ceil(1000000 / (round((1 / 20) * (2 / 50) * W.SamplingRate) + round((1 / 20) * (48 / 50) * W.SamplingRate)))); % Repeat that pulse as often as it is needed to get at least one million samples
Pulse20Hz = Pulse20Hz(1:1000000); % Cut the repeated cue back down to exactly one million samples (maximum length for the WavePlayer).
Standing = 5 * ones(1, 1000000)'; % Just a long row of 5V
% Slightly more complicated: the sine-wave
f=20; % The frequency
Amp=2.5; % The amplitude
ts=1 / W.SamplingRate; % Time for each sample
T= 1000000 / W.SamplingRate; % Total amount of time
t=0:ts:T-ts; % The time-steps used to generate the sine-wave
Sine20Hz = (Amp * sin(2*pi*f*t) + 2.5)'; % The finished sine-wave for 1000000 samples between 5V and 0V and with 20Hz
% Loading the generated waveforms with a ' so they have the correct format
% (transposed matrix, because the WavePlayer expects columns, not rows)
W.loadWaveform(3, Pulse20Hz');
W.loadWaveform(4, Standing');
W.loadWaveform(5, Sine20Hz');

%% If a cam is used, define the second waveplayer-object and load the trigger
if CamTrigger % if enabed, a WavePlayer MUST be connected to the correct port, otherwise the protocol will end with an error
    WCam = BpodWavePlayer('COM9'); % WIP: COM-Port needs to be adapted to current setup
    WCam.OutputRange = strcat('-', num2str(5), 'V:', num2str(5), 'V'); % OutputRange is set to -5V:5V for the cam-trigger.

    % As a trigger the pulse-wave from the previous segment is adapted to 100Hz
    % with a duty-cycle of 0.1.
    myMat = [5 * ones(1, round((1 / 100) * (1 / 10) * W.SamplingRate)), zeros(1, round((1 / 100) * (9 / 10) * W.SamplingRate))]; % A single pulse of 1ms 5V and 9ms 0V
    Pulse100Hz = repmat(myMat, 1, ceil(1000000 / (round((1 / 100) * (2 / 50) * W.SamplingRate) + round((1 / 100) * (48 / 50) * W.SamplingRate)))); % Repeat that pulse as often as it is needed to get at least one million samples
    Pulse100Hz = Pulse2100Hz(1:1000000); % Cut the repeated cue back down to exactly one million samples (maximum length for the WavePlayer).

    WCam.loadWaveform(1, Pulse100Hz'); % Load the previously generated trigger into waveform 1 on the second WavePlayer
end
%% Define serial messages being sent to modules
LoadSerialMessages('WavePlayer1', {['P' 2 2], ['P' 2 3], ['P' 2 4], ['P' 1 1], ['P' 1 0], ['X']});
% WavePlayer1:
% command 1: play pulse 20Hz, command 2: play standing signal
% command 3: play sine wave 20Hz
% Command 4: play start-cue, command 5: play failure-cue,
% command 6: end all playback
% command 1&2&3 are on channel 2, command 4&5 are on channel 1

% WavePlayer2:
% command 1: play pulse 100Hz (trigger), command 2: end all playback

%% Define trials
% Left-right trial is determined by comparing a random number against a
% bias and using the boolean 0 or 1 as the trialtype
TrialTypes = double(rand(1, MaxTrials)>S.GUI.Bias); % The projected sequence of trials.
oldBias = S.GUI.Bias; % Remembering this allows us to redraw the projected trials on the fly.
BpodSystem.Data.TrialTypes = []; % The trial type of each trial completed will be added here.

% LED trials are determined by creating a utility matrix, which at first
% only has lines of zeros. For every possible phase the matrix is
% extended by a line of uniform random numbers, if that phase is enabled.
% Otherwise the line remains at zero. To finally find the random
% distribution of phases, the maximum for each column is determined. Due to
% the uniform distribution of the random lines, this value is uniformly
% distributed, too, and defaults to line 1 (first line of zeros) if no
% phase is enabled.

LEDMatrix = zeros(4, MaxTrials); % A utility matrix which is used to generate the random distribution for the LED-trials.
if S.GUI.AirpuffLED
    LEDMatrix(2,:) = rand(1, MaxTrials);
end
if S.GUI.DelayPeriodLED
    LEDMatrix(3,:) = rand(1, MaxTrials);
end
if S.GUI.ResponsePeriodLED
    LEDMatrix(4,:) = rand(1, MaxTrials);
end
[M, LEDTypes] = max(LEDMatrix); % M is here only necessary to get the index of the maximum values.
oldAirpuffLED = S.GUI.AirpuffLED;
oldDelayPeriodLED = S.GUI.DelayPeriodLED;
oldResponsePeriodLED = S.GUI.ResponsePeriodLED;
% Remembering these values allows the recalculation of the distribution in
% real-time.
BpodSystem.Data.LEDTypes = []; % The  LED type of each trial completed will be added here.
BpodSystem.Data.Reaching = []; % Whether or not the mouse had to reach during the current trial. false = licking, true = reaching,
BpodSystem.Data.RandomValues.DelayPeriodDuration = []; % The randomized length of the delay periods of each trial completed will be added here.

%% Define counters
% These are necessary to allow the real-time bias-calculation
LeftRewards = 0;
RightRewards = 0;

ReachingSwitch = 1 + S.GUI.ReachingTaskBlockSize; % First trial during which we switch between licking and reaching.
oldAutomatedReaching = S.GUI.AutomatedReaching;
oldReachingTaskBlockSize = S.GUI.ReachingTaskBlockSize;

%% Initialize plots
BpodSystem.ProtocolFigures.OutcomePlotFig = figure('Position', [50 540 1000 250],'name','Outcome plot','numbertitle','off', 'Toolbar', 'none', 'Resize', 'off');
BpodSystem.GUIHandles.OutcomePlot = axes('Position', [.075 .3 .89 .6]);
SideOutcomePlot(BpodSystem.GUIHandles.OutcomePlot,'init',TrialTypes);
SideOutcomePlot(BpodSystem.GUIHandles.OutcomePlot,'update',1,TrialTypes,0); % Since the SideOutcomePlot initializes on trial 0, which then skips to 2, it is immediately updated here

% A lot of the following blocs is necessary to have the axes and legends at
% a static position and being able to have 2 legends in 1 plot.
% Also this code allows us to hide the legends, by just decreasing the
% width of the window and hiding them behind the right border.

% Set axes and figure units to pixels, get current positions
set(BpodSystem.ProtocolFigures.OutcomePlotFig,'Units','pixels')
set(BpodSystem.GUIHandles.OutcomePlot,'Units','pixels')
fig_pos = get(BpodSystem.ProtocolFigures.OutcomePlotFig,'position');
old_ax_pos = get(BpodSystem.GUIHandles.OutcomePlot,'position');

% Lots of work to get 2 legends to show
% Since we probably wont see all of the possible outcomes, but still want
% them to show in the legend, we create empty plots with the proper
% markings. Since we only use 4 of the possible 5 outcomes, we create only 
% 4 plots. The DisplayName will be later shown in the legends.

OC = zeros(4, 1); % An array representing the possible outcomes
OC(1) = scatter(NaN,NaN,'o', 'MarkerFaceColor', 'g', 'MarkerEdgeColor', 'none', 'DisplayName', 'Reward', 'Parent', BpodSystem.GUIHandles.OutcomePlot); % Reward
OC(2) = scatter(NaN,NaN,'or', 'DisplayName', 'Too early lick', 'Parent', BpodSystem.GUIHandles.OutcomePlot); % Failure Type 1
OC(3) = scatter(NaN,NaN,'ob', 'DisplayName', 'No lick', 'Parent', BpodSystem.GUIHandles.OutcomePlot); % Failure Type 2
OC(4) = scatter(NaN,NaN,'o', 'MarkerFaceColor', 'r', 'MarkerEdgeColor', 'none', 'DisplayName','Wrong side lick', 'Parent', BpodSystem.GUIHandles.OutcomePlot); % Failure Type 3

Legends = zeros(2, 1); % An array holding the two legends
Legends(1) = legend(OC, 'location', 'northeastoutside', 'FontSize', 10, 'Units', 'pixels'); % First legend
title(Legends(1), 'Outcomes')

Ax2 = copyobj(BpodSystem.GUIHandles.OutcomePlot,gcf); % copy the axis
set(Ax2,'Units','pixels') % set its units to pixels
delete(get(Ax2,'Children')) % delete its children
Ax2.Visible = 'off'; % make it invisible

PM = zeros(2, 1); % An array representing the possible parameters, LED and reaching
PM(1) = patch([NaN NaN NaN NaN],[NaN NaN NaN NaN],[0 .75 .75],'LineStyle','none','FaceAlpha',0.4,'DisplayName', 'Reaching task', 'Parent', Ax2); % Reaching task active
PM(2) = patch([NaN NaN NaN NaN],[NaN NaN NaN NaN],[.85 .85 0],'LineStyle','none','FaceAlpha',1,'DisplayName', 'LED active', 'Parent', Ax2); % LED active

Legends(2) = legend(PM, 'location', 'southeastoutside', 'FontSize', 10, 'Units', 'pixels'); % Second legend
P1 = get(Legends(1), 'position');
P2 = get(Legends(2), 'position');
P2(3) = P1(3); % Set the width of the second legend to the width of the first legend
P2(1) = P1(1) + P2(3) + 11; % due to different reference points in the two axes, the second legend needs a little more shifting to get to the same x-position as the first legend. No idea why though.
set(Legends(2), 'position', P2); % Update the position of the second legend with the new, correct coordinates
title(Legends(2), 'Parameters')

% Get the new axes position, look at how much it shifted
new_ax_pos = get(BpodSystem.GUIHandles.OutcomePlot,'position');
pixel_shift = new_ax_pos - old_ax_pos;

% Make figure wider and restore axes width to their initial value
set(BpodSystem.ProtocolFigures.OutcomePlotFig, 'position',fig_pos - [0 0 pixel_shift(3) 0]);
set(BpodSystem.GUIHandles.OutcomePlot,'position',old_ax_pos + [pixel_shift(1) 0 0 0]);
set(Ax2,'position',get(BpodSystem.GUIHandles.OutcomePlot, 'position')); % Move the second axes to the same position as the original axes.

Annotations = zeros(3,1); % Annotations below the ticks on the y-axis which will show the currently active LED-state, together with the rectangles which are drawn later
Annotations(1) = annotation('textbox',[.0 .27 .1 .2],'String','AirpuffLED','EdgeColor','none', 'FontSize', 7);
Annotations(2) = annotation('textbox',[.0 .22 .1 .2],'String','DelayLED','EdgeColor','none', 'FontSize', 7);
Annotations(3) = annotation('textbox',[.0 .17 .1 .2],'String','ResponseLED','EdgeColor','none', 'FontSize', 7);

BpodNotebook('init'); % Initialize Bpod notebook (for manual data annotation)
BpodParameterGUI('init', S); % Initialize parameter GUI plugin
TotalRewardDisplay('init'); % Initialize the total reward display

%% Make the legend and other stuff toggleable
m = uimenu(BpodSystem.ProtocolFigures.OutcomePlotFig,'Text','&Plot Options'); % Create a new menu-point for our custom options
mitem1 = uimenu(m,'Text','Show legends','Checked','on'); % An option to hide the legends
mitem1.MenuSelectedFcn = @ShowLegend;
mitem2 = uimenu(m,'Text','Show active LED states','Checked','on'); % An option to hide the active LED-states
mitem2.MenuSelectedFcn = @ShowLED;
mitem3 = uimenu(m,'Text','Show reaching task trials','Checked','on'); % An option to hide the markings for reaching task trials
mitem3.MenuSelectedFcn = @ShowReaching;

    function ShowLegend(src,event) % A function that hides the legends by shrinking the window, or shows them by increasing its width
        if strcmp(mitem1.Checked,'on')
            mitem1.Checked = 'off';
            set(BpodSystem.ProtocolFigures.OutcomePlotFig, 'position',fig_pos - [0 0 22 0]);
        else
            mitem1.Checked = 'on';
            set(BpodSystem.ProtocolFigures.OutcomePlotFig, 'position',fig_pos - [0 0 pixel_shift(3) 0]);
        end
    end

    function ShowLED(src,event) % A function that toggles the annotations and rectangles used for the LED-states
        Rectangles = findall(get(BpodSystem.GUIHandles.OutcomePlot, 'Children'), 'FaceColor', [0.85 0.85 0 1]);
        if strcmp(mitem2.Checked,'on')
            mitem2.Checked = 'off';
            set(Annotations, 'visible', 'off')
            set(Rectangles, 'visible', 'off')
        else
            mitem2.Checked = 'on';
            set(Annotations, 'visible', 'on')
            set(Rectangles, 'visible', 'on')
        end
    end

    function ShowReaching(src,event) % A function that toggles the transparent rectangles used for the reaching trials
        Rectangles = findall(get(BpodSystem.GUIHandles.OutcomePlot, 'Children'), 'FaceColor', [0 0.75 0.75 0.4]);
        if strcmp(mitem3.Checked,'on')
            mitem3.Checked = 'off';
            set(Rectangles, 'visible', 'off')
        else
            mitem3.Checked = 'on';
            set(Rectangles, 'visible', 'on')
        end
    end

%% Main loop (runs once per trial)
for currentTrial = 1:MaxTrials
    R = GetValveTimes(S.GUI.RewardAmount, [1 3]); LeftValveTime = R(1); RightValveTime = R(2); % Update reward amounts
    % For all following blocs it will be assumed that the left ports are
    % air on port 1, reward on port 2 and the right ports are air on port 3
    % and reward on port 4
    
    %--- Typically, a block of code here will compute variables for assembling this trial's state machine
    if oldBias ~= S.GUI.Bias % Check if someone changed the bias manually
        oldBias = S.GUI.Bias;
        S.GUI.BiasAutoAdjust = 0; % Once someone changed the bias manually, switch autoadjust off until it gets manually reactivated
        disp('Bias was adjusted.')
        TrialTypes(currentTrial:MaxTrials) = [rand(1, MaxTrials - currentTrial + 1)>S.GUI.Bias]; % 0 is right, 1 is left
        SideOutcomePlot(BpodSystem.GUIHandles.OutcomePlot,'update',BpodSystem.Data.nTrials+1,TrialTypes,Outcomes); % Update the Plot
    
    elseif mod(currentTrial, BiasAdjustmentSteps) == 0 && (S.GUI.BiasAutoAdjust == 1) && (LeftRewards > 0) && (RightRewards > 0)
        % If the current trial is a multiple of the BiasAdjustmentSteps AND
        % AutoAdjust is activated AND both rewards were at least once
        % dispensed, then calculate a new bias, based on the dispensed
        % rewards.
        newBias = LeftRewards / (RightRewards + LeftRewards);
        if oldBias ~= newBias % Check if the newly calculated bias is the same as before.
            [oldBias, S.GUI.Bias] = deal(newBias);
            TrialTypes(currentTrial:MaxTrials) = [rand(1, MaxTrials - currentTrial + 1)>S.GUI.Bias]; % 0 is right, 1 is left
            SideOutcomePlot(BpodSystem.GUIHandles.OutcomePlot,'update',BpodSystem.Data.nTrials+1,TrialTypes,Outcomes); % Update the Plot
        end
    end
    
    if (oldAirpuffLED ~= S.GUI.AirpuffLED) || (oldDelayPeriodLED ~= S.GUI.DelayPeriodLED) || (oldResponsePeriodLED ~= S.GUI.ResponsePeriodLED) % If something changed during the last trial, recalculate the projected sequence of LED-states
        LEDMatrix = zeros(4, MaxTrials); % A utility matrix which is used to generate the random distribution for the LED-trials.
        if S.GUI.AirpuffLED
            LEDMatrix(2,:) = rand(1, MaxTrials);
        end
        if S.GUI.DelayPeriodLED
            LEDMatrix(3,:) = rand(1, MaxTrials);
        end
        if S.GUI.ResponsePeriodLED
            LEDMatrix(4,:) = rand(1, MaxTrials);
        end
        [M, LEDTypes] = max(LEDMatrix); % M is here only necessary to get the index of the maximum values.
        oldAirpuffLED = S.GUI.AirpuffLED;
        oldDelayPeriodLED = S.GUI.DelayPeriodLED;
        oldResponsePeriodLED = S.GUI.ResponsePeriodLED;
    end

    S = BpodParameterGUI('sync', S);    % Sync parameters with BpodParameterGUI plugin
                                        % This was moved down, so the newly
                                        % calculated bias could be
                                        % displayed immediately.

    DelayPeriodDuration = S.GUI.DelayPeriodMean + S.GUI.DelayPeriodRange * (2 * (rand - 0.5)); % Calculate the random delay period length
    
    switch TrialTypes(currentTrial) % Determine trial-specific state matrix fields
        case 0
            StateOnLeftPort = 'PreFailure3'; StateOnRightPort = 'RightReward';
            AirPuff = 'RightPuff';
            S.GUI.RewardDuration = RightValveTime;
        case 1
            StateOnLeftPort = 'LeftReward'; StateOnRightPort = 'PreFailure3';
            AirPuff = 'LeftPuff';
            S.GUI.RewardDuration = LeftValveTime;
    end
    
    switch S.GUI.AutoReward % Decide whether reward will be dispensed automatically after the AutoRewardPeriod or the mouse has to lick in the ResponsePeriod
        case 0
            ResponsePeriod = 'ResponsePeriod';
            RewardState = 'PreFailure2'; % Dummy-value, should be never used
        case 1
            switch TrialTypes(currentTrial)
                case 0
                    ResponsePeriod = 'AutoRewardPeriod';
                    RewardState = 'RightReward';
                case 1
                    ResponsePeriod = 'AutoRewardPeriod';
                    RewardState = 'LeftReward';
            end
    end
    
    DelayPeriod  = 'DelayPeriod';
    
    if rand<S.GUI.IlluminationProbability
        switch LEDTypes(currentTrial)
            case 1
                % Default case, no LED-phases are selected
            case 2
                AirPuff = strcat('LED', AirPuff);
                figure(BpodSystem.ProtocolFigures.OutcomePlotFig);
                rectangle('Position', [currentTrial-0.5 -0.475  1 0.225], 'FaceColor', [0.85 0.85 0 1], 'EdgeColor', 'none');
            case 3
                DelayPeriod = strcat('LED', DelayPeriod);
                figure(BpodSystem.ProtocolFigures.OutcomePlotFig);
                rectangle('Position', [currentTrial-0.5 -0.7125  1 0.225], 'FaceColor', [0.85 0.85 0 1], 'EdgeColor', 'none');
            case 4
                ResponsePeriod = strcat('LED', ResponsePeriod);
                figure(BpodSystem.ProtocolFigures.OutcomePlotFig);
                rectangle('Position', [currentTrial-0.5 -0.95  1 0.225], 'FaceColor', [0.85 0.85 0 1], 'EdgeColor', 'none');
        end
    end
    
    LEDSignal = S.GUI.LEDSignal; % Index of the dropdown-menu is at the same time the index of the corresponding signal.
    
    if (S.GUI.AutomatedReaching && ~oldAutomatedReaching) || (oldReachingTaskBlockSize ~= S.GUI.ReachingTaskBlockSize)
        ReachingSwitch = currentTrial + S.GUI.ReachingTaskBlockSize; % Set the switchpoint ReachingTaskBlockSize steps ahead, if automated raching was just activated.
        oldReachingTaskBlockSize = S.GUI.ReachingTaskBlockSize; % If something changed about the S.GUI.ReachingTaskBlockSize then update the switchpoint
    end
    oldAutomatedReaching = S.GUI.AutomatedReaching;
        
    if CamTrigger
        StartState = 'CamTrigger'; % if the camtrigger is enabled, it should be played after the reaching switch
    else
        StartState = 'InitialDelay'; % otherwise go on to the initial delay-state
    end
    %--- Assemble state machine
    sma = NewStateMachine();
        
    if S.GUI.AutomatedReaching && (currentTrial >= ReachingSwitch)
        ReachingSwitch = currentTrial + S.GUI.ReachingTaskBlockSize; % Set the switchpoint ReachingTaskBlockSize steps ahead.
        S.GUI.ReachingTask = ~S.GUI.ReachingTask;
        S = BpodParameterGUI('sync', S); % Sync, so that the new setting is displayed in real-time
        switch S.GUI.ReachingTask
            case false
                sma = AddState(sma, 'Name', 'ReachingSwitch', ...
                    'Timer', 3,...
                    'StateChangeConditions', {'Tup', StartState},...
                    'OutputActions', {'BNC1', true}); 
                % All this state does is giving the micromanipulator enough time to
                % switch to the licking configuration.
            case true
                sma = AddState(sma, 'Name', 'ReachingSwitch', ...
                    'Timer', 3,...
                    'StateChangeConditions', {'Tup', StartState},...
                    'OutputActions', {'BNC2', true}); 
                % All this state does is giving the micromanipulator enough time to
                % switch to the reaching configuration.
        end
        
    elseif currentTrial == 1
        switch S.GUI.ReachingTask
            case false
                sma = AddState(sma, 'Name', 'ReachingSwitch', ...
                    'Timer', 3,...
                    'StateChangeConditions', {'Tup', StartState},...
                    'OutputActions', {'BNC1', true});
                % All this state does is giving the micromanipulator enough time to
                % switch to the licking configuration.
            case true
                sma = AddState(sma, 'Name', 'ReachingSwitch', ...
                    'Timer', 3,...
                    'StateChangeConditions', {'Tup', StartState},...
                    'OutputActions', {'BNC2', true});
                % All this state does is giving the micromanipulator enough time to
                % switch to the reaching configuration.
        end
        % This is necessary during the first trial to guarantee
        % synchronized states between the micromanipulator and the Bpod.
    end
    
    if S.GUI.ReachingTask % If the current trial is a reaching task, then mark it on the plot with a transparent background (alpha = 0.4)
        figure(BpodSystem.ProtocolFigures.OutcomePlotFig);
        rectangle('Position', [currentTrial-0.5 -1  1 3], 'FaceColor', [0 0.75 0.75 0.4], 'EdgeColor', 'none')
    end

    if CamTrigger
        sma = AddState(sma, 'Name', 'CamTrigger', ...
            'Timer', 0,...
            'StateChangeConditions', {'Tup', 'InitialDelay'},...
            'OutputActions', {'WavePlayer2', 1}); 
        % All this state does is to start the trigger for the cam (if enabled).
    end
        
    sma = AddState(sma, 'Name', 'InitialDelay', ...
        'Timer', S.GUI.InitialDelay,...
        'StateChangeConditions', {'BNC1High', 'InitialDelayLoop', 'BNC2High', 'InitialDelayLoop', 'Tup', AirPuff},...
        'OutputActions', {}); 
    % If there is any input to either licking port, the inital delay will
    % restart. The length can be changed in between trials.
    
    sma = AddState(sma, 'Name', 'InitialDelayLoop', ...
        'Timer', 0,...
        'StateChangeConditions', {'Tup', 'InitialDelay'},...
        'OutputActions', {});
    % This little loop-state is necessary, since linking from a state to
    % itself wont restart its timer. For example, were the mouse to
    % permanently lick during the initial delay and that state would only
    % link to itself again, the timer would run out despite the repeated
    % licking.
    
    sma = AddState(sma, 'Name', 'LeftPuff', ...
        'Timer', S.GUI.PuffLength,...
        'StateChangeConditions', {'BNC1High', 'PreFailure1', 'BNC2High', 'PreFailure1', 'Tup', DelayPeriod},...
        'OutputActions', {'Valve1', true}); 
    sma = AddState(sma, 'Name', 'RightPuff', ...
        'Timer', S.GUI.PuffLength,...
        'StateChangeConditions', {'BNC1High', 'PreFailure1', 'BNC2High', 'PreFailure1', 'Tup', DelayPeriod},...
        'OutputActions', {'Valve4', true}); 
    % While the airpuff is applied, any licking will result in a failure of
    % type 1, same as in the delay period.
    
    sma = AddState(sma, 'Name', 'LEDLeftPuff', ...
        'Timer', S.GUI.PuffLength,...
        'StateChangeConditions', {'BNC1High', 'PreFailure1', 'BNC2High', 'PreFailure1', 'Tup', 'PostLEDAirPuff'},...
        'OutputActions', {'Valve1', true, 'WavePlayer1', LEDSignal}); 
    sma = AddState(sma, 'Name', 'LEDRightPuff', ...
        'Timer', S.GUI.PuffLength,...
        'StateChangeConditions', {'BNC1High', 'PreFailure1', 'BNC2High', 'PreFailure1', 'Tup', 'PostLEDAirPuff'},...
        'OutputActions', {'Valve4', true, 'WavePlayer1', LEDSignal}); 
    % While the airpuff is applied, any licking will result in a faile of
    % type 1, same as in the delay period. These alternative states contain
    % an illumination signal on channel 2 of the analog output module.
    
    sma = AddState(sma, 'Name', 'PostLEDAirPuff', ...
        'Timer', 0,...
        'StateChangeConditions', {'BNC1High', 'PreFailure1', 'BNC2High', 'PreFailure1', 'Tup', 'DelayPeriod'},...
        'OutputActions', {'WavePlayer1', 6});
    % This state is used to switch the LED off after it was on during the
    % previous state.
    
    sma = AddState(sma, 'Name', 'DelayPeriod', ...
        'Timer', DelayPeriodDuration,...
        'StateChangeConditions', {'BNC1High', 'PreFailure1', 'BNC2High', 'PreFailure1', 'Tup', 'Sound'},...
        'OutputActions', {}); 
    % During the delay period any early licking will lead to a failure of
    % type 1. Its length is based on the mean and the range given in the
    % GUI.
    
    sma = AddState(sma, 'Name', 'LEDDelayPeriod', ...
        'Timer', DelayPeriodDuration,...
        'StateChangeConditions', {'BNC1High', 'PreFailure1', 'BNC2High', 'PreFailure1', 'Tup', 'PostLEDDelayPeriod'},...
        'OutputActions', {'WavePlayer1', LEDSignal}); 
    % During the delay period any early licking will lead to a failure of
    % type 1. Its length is based on the mean and the range given in the
    % GUI. This alternative state contains an illumination signal on
    % channel 2 of the analog output module.
    
    sma = AddState(sma, 'Name', 'PostLEDDelayPeriod', ...
        'Timer', 0,...
        'StateChangeConditions', {'BNC1High', 'PreFailure1', 'BNC2High', 'PreFailure1', 'Tup', 'Sound'},...
        'OutputActions', {'WavePlayer1', 6}); 
    % This state is used to switch the LED off after it was on during the
    % previous state.
        
    sma = AddState(sma, 'Name', 'Sound', ...
        'Timer', 0,...
        'StateChangeConditions', {'BNC1High', 'PreFailure1', 'BNC2High', 'PreFailure1', 'Tup', ResponsePeriod},...
        'OutputActions', {'WavePlayer1', 4}); 
    % This state is used to tell the analog output module to play the start
    % sound which is used to signal the end of the delay period.  If
    % auto-reward is enabled, the response period will be replaced with
    % blind period, during which nothing happens, until the reward is
    % dispensed on the correct side.
    % Licks during this phase lead to a failure of type 1.
    
    sma = AddState(sma, 'Name', 'PreFailure1', ...
        'Timer', 0,...
        'StateChangeConditions', {'Tup', 'Failure1'},...
        'OutputActions', {'WavePlayer1', 6}); 
    % Due to the pecularites of state machines, the abort signal needs to
    % be sent during a separate state, before a new cue, the failure cue,
    % can be played. Otherwise it cant be guaranteed that the output module
    % reacts to the abort and the new signal in the proper order, resulting
    % in no cue being played.
    
    sma = AddState(sma, 'Name', 'Failure1', ...
        'Timer', S.GUI.FailureLength,...
        'StateChangeConditions', {'Tup', 'FailureInterval'},...
        'OutputActions', {'WavePlayer1', 5}); 
    % Should a failure of any type occur, a fail cue will be played and the
    % trial ends.
    
    sma = AddState(sma, 'Name', 'ResponsePeriod', ...
        'Timer', S.GUI.ResponsePeriod,...
        'StateChangeConditions', {'BNC1High', StateOnLeftPort, 'BNC2High', StateOnRightPort, 'Tup', 'PreFailure2'},...
        'OutputActions', {}); 
    % During this state the mouse can attempt to lick. If it licks the
    % wrong side, it will result in a failure of type 3. If it doesnt lick
    % at all, it will result in a failure type 2.
    
    sma = AddState(sma, 'Name', 'LEDResponsePeriod', ...
        'Timer', S.GUI.ResponsePeriod,...
        'StateChangeConditions', {'BNC1High', 'PostLEDResponsePeriodLeft', 'BNC2High', 'PostLEDResponsePeriodRight', 'Tup', 'PreFailure2'},...
        'OutputActions', {'WavePlayer1', LEDSignal}); 
    % During this state the mouse can attempt to lick. If it licks the
    % wrong side, it will result in a failure of type 3. If it doesnt lick
    % at all, it will result in a failure type 2. This alternative state
    % contains an illumination signal on channel 2 of the analog output 
    % module.
    
    sma = AddState(sma, 'Name', 'PostLEDResponsePeriodLeft', ...
        'Timer', 0,...
        'StateChangeConditions', {'Tup', StateOnLeftPort},...
        'OutputActions', {'WavePlayer1', 6});
    sma = AddState(sma, 'Name', 'PostLEDResponsePeriodRight', ...
        'Timer', 0,...
        'StateChangeConditions', {'Tup', StateOnRightPort},...
        'OutputActions', {'WavePlayer1', 6}); 
    % These two states are used to switch the LED off after it was on
    % during the previous state. Two states are required to remember the
    % correct assignment of reward and failure to the two sides.
    
    sma = AddState(sma, 'Name', 'AutoRewardPeriod', ...
        'Timer', S.GUI.ResponsePeriod,...
        'StateChangeConditions', {'Tup', RewardState},...
        'OutputActions', {});
    % During this state the mouse has to wait, until the reward is
    % dispensed automatically. It is only used if autoreward is enabled and
    % lasts the same duration as the normal response period.
    
    sma = AddState(sma, 'Name', 'LEDAutoRewardPeriod', ...
        'Timer', S.GUI.ResponsePeriod,...
        'StateChangeConditions', {'Tup', 'PostLEDAutoRewardPeriod'},...
        'OutputActions', {'WavePlayer1', LEDSignal});
    % During this state the mouse has to wait, until the reward is
    % dispensed automatically. It is only used if autoreward is enabled and
    % lasts the same duration as the normal response period. This
    % alternative state contains an illumination signal on channel 2 of the
    % analog output module.

    sma = AddState(sma, 'Name', 'PostLEDAutoRewardPeriod', ...
        'Timer', 0,...
        'StateChangeConditions', {'Tup', RewardState},...
        'OutputActions', {'WavePlayer1', 6}); 
    % This state is used to switch the LED off after it was on during the
    % previous state.
    
    sma = AddState(sma, 'Name', 'PreFailure2', ...
        'Timer', 0,...
        'StateChangeConditions', {'Tup', 'Failure2'},...
        'OutputActions', {'WavePlayer1', 6});
    sma = AddState(sma, 'Name', 'PreFailure3', ...
        'Timer', 0,...
        'StateChangeConditions', {'Tup', 'Failure3'},...
        'OutputActions', {'WavePlayer1', 6}); 
    % Due to the pecularites of state machines, the abort signal needs to
    % be sent during a separate state, before a new cue, the failure cue,
    % can be played. Otherwise it cant be guaranteed that the output module
    % reacts to the abort and the new signal in the proper order, resulting
    % in no cue being played.

    sma = AddState(sma, 'Name', 'Failure2', ...
        'Timer', S.GUI.FailureLength,...
        'StateChangeConditions', {'Tup', 'FailureInterval'},...
        'OutputActions', {'WavePlayer1', 5}); 
    % Should a failure of any type occur, a fail cue will be played and the
    % trial ends.

    sma = AddState(sma, 'Name', 'Failure3', ...
        'Timer', S.GUI.FailureLength,...
        'StateChangeConditions', {'Tup', 'FailureInterval'},...
        'OutputActions', {'WavePlayer1', 5}); 
    % Should a failure of any type occur, a fail cue will be played and the
    % trial ends.
    
    sma = AddState(sma, 'Name', 'FailureInterval', ...
        'Timer', S.GUI.InterTrialIntervalFailure,...
        'StateChangeConditions', {'Tup', 'exit'},...
        'OutputActions', {'WavePlayer1', 6}); 
    % A shorter phase after a failed trial, before a new trial begins. Here
    % are also all failure-cues stopped for the next trial.

    sma = AddState(sma, 'Name', 'LeftReward', ...
        'Timer', LeftValveTime,...
        'StateChangeConditions', {'Tup', 'InterTrialInterval'},...
        'OutputActions', {'Valve2', true, 'WavePlayer1', 6});
    sma = AddState(sma, 'Name', 'RightReward', ...
        'Timer', RightValveTime,...
        'StateChangeConditions', {'Tup', 'InterTrialInterval'},...
        'OutputActions', {'Valve3', true, 'WavePlayer1', 6});
    % The reward will be dispensed on the corresponding side in these two
    % states. They also end the cue from the previous state, if auto-reward
    % is enabled.
    
    sma = AddState(sma, 'Name', 'InterTrialInterval', ...
        'Timer', S.GUI.InterTrialInterval,...
        'StateChangeConditions', {'Tup', 'exit'},...
        'OutputActions', {}); 
    % A final phase before the next trial begins.
    
    SendStateMatrix(sma); % Send state machine to the Bpod state machine device
    RawEvents = RunStateMatrix; % Run the trial and return events
    
    %--- Package and save the trial's data, update plots
    if ~isempty(fieldnames(RawEvents)) % If you didn't stop the session manually mid-trial
        BpodSystem.Data = AddTrialEvents(BpodSystem.Data,RawEvents); % Adds raw events to a human-readable data struct
        BpodSystem.Data.TrialSettings(currentTrial) = S; % Adds the settings used for the current trial to the Data struct (to be saved after the trial ends)
        BpodSystem.Data.TrialTypes(currentTrial) = TrialTypes(currentTrial); % Adds the trial type of the current trial to data
        BpodSystem.Data.LEDTypes(currentTrial) = LEDTypes(currentTrial); % Adds the LED type of the current trial to data
        BpodSystem.Data.Reaching(currentTrial) = S.GUI.ReachingTask; % The same value can be seen in the settings.
        BpodSystem.Data.RandomValues.DelayPeriodDuration(currentTrial) = DelayPeriodDuration;
        SaveBpodSessionData; % Saves the field BpodSystem.Data to the current data file
        
        %--- Checking if the currentTrial resulted in a reward
        if (~isnan(BpodSystem.Data.RawEvents.Trial{currentTrial}.States.LeftReward(1))) % A LeftReward was dispensed, left counter increases
            LeftRewards = LeftRewards + 1;
            TotalRewardDisplay('add', S.GUI.RewardAmount); % The dispensed amount is also added to the TotalRewardDisplay
        elseif (~isnan(BpodSystem.Data.RawEvents.Trial{currentTrial}.States.RightReward(1))) % A RightReward was dispensed, right counter increases
            RightRewards = RightRewards + 1;
            TotalRewardDisplay('add', S.GUI.RewardAmount); % The dispensed amount is also added to the TotalRewardDisplay
        end

        
        %--- Typically a block of code here will update online plots using the newly updated BpodSystem.Data
        Outcomes = zeros(1,BpodSystem.Data.nTrials);
        for x = 1:BpodSystem.Data.nTrials
            if (~isnan(BpodSystem.Data.RawEvents.Trial{x}.States.LeftReward(1)))
                Outcomes(x) = 1; % Rewards are marked with a filled green circle.
            elseif (~isnan(BpodSystem.Data.RawEvents.Trial{x}.States.RightReward(1)))
                Outcomes(x) = 1; % Rewards are marked with a filled green circle.
            elseif (~isnan(BpodSystem.Data.RawEvents.Trial{x}.States.Failure1(1)))
                Outcomes(x) = -1; % Failures of type 1 are marked with an unfilled red circle.
            elseif (~isnan(BpodSystem.Data.RawEvents.Trial{x}.States.Failure2(1)))
                Outcomes(x) = 3; % Failures of type 2 are marked with an unfilled blue circle.
            elseif (~isnan(BpodSystem.Data.RawEvents.Trial{x}.States.Failure3(1)))
                Outcomes(x) = 0; % Failures of type 3 are marked with a filled red circle.
            else
                Outcomes(x) = 3; % The default case is a failure of type 2 (no licks)
            end
            % Since 5 markers are available, we have 1 marker (index 2), an
            % unfilled green circle, left.
        end
    SideOutcomePlot(BpodSystem.GUIHandles.OutcomePlot,'update',BpodSystem.Data.nTrials+1,TrialTypes,Outcomes); % Update the SideOutcomePlot with the new results from all previous and the current trial.
    end
    
    %--- This final block of code is necessary for the Bpod console's pause and stop buttons to work
    HandlePauseCondition; % Checks to see if the protocol is paused. If so, waits until user resumes.
    if BpodSystem.Status.BeingUsed == 0
        return
    end
end

clear W % Clear the Waveplayer after a successful run, so the COM-Object can be used again.
end