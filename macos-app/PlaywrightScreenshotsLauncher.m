#import <Cocoa/Cocoa.h>
#import <signal.h>

@interface AppController : NSObject <NSApplicationDelegate, NSWindowDelegate>
@property(nonatomic, strong) NSWindow *window;
@property(nonatomic, strong) NSTextField *statusLabel;
@property(nonatomic, strong) NSTextField *detailLabel;
@property(nonatomic, strong) NSTextField *urlLabel;
@property(nonatomic, strong) NSTextView *logView;
@property(nonatomic, strong) NSButton *startButton;
@property(nonatomic, strong) NSButton *openButton;
@property(nonatomic, strong) NSButton *stopButton;
@property(nonatomic, strong) NSButton *revealButton;
@property(nonatomic, strong) NSTask *serverTask;
@property(nonatomic, strong) NSPipe *outputPipe;
@property(nonatomic, strong) NSMutableString *lineBuffer;
@property(nonatomic, strong) NSURL *serverURL;
@property(nonatomic, assign) BOOL browserOpenedAutomatically;
@property(nonatomic, assign) BOOL quitAfterShutdown;
@end

@implementation AppController

- (NSColor *)bodyTextColor {
    return [NSColor colorWithCalibratedRed:0.33 green:0.39 blue:0.37 alpha:1.0];
}

- (NSColor *)buttonBackgroundColorForRole:(NSString *)role enabled:(BOOL)enabled {
    if (!enabled) {
        return [NSColor colorWithCalibratedRed:0.91 green:0.92 blue:0.90 alpha:1.0];
    }
    if ([role isEqualToString:@"primary"]) {
        return [NSColor colorWithCalibratedRed:0.10 green:0.38 blue:0.30 alpha:1.0];
    }
    if ([role isEqualToString:@"danger"]) {
        return [NSColor colorWithCalibratedRed:0.95 green:0.89 blue:0.89 alpha:1.0];
    }
    return [NSColor colorWithCalibratedRed:0.90 green:0.95 blue:0.92 alpha:1.0];
}

- (NSColor *)buttonBorderColorForRole:(NSString *)role enabled:(BOOL)enabled {
    if (!enabled) {
        return [NSColor colorWithCalibratedRed:0.71 green:0.75 blue:0.71 alpha:1.0];
    }
    if ([role isEqualToString:@"primary"]) {
        return [NSColor colorWithCalibratedRed:0.10 green:0.38 blue:0.30 alpha:1.0];
    }
    if ([role isEqualToString:@"danger"]) {
        return [NSColor colorWithCalibratedRed:0.78 green:0.55 blue:0.55 alpha:1.0];
    }
    return [NSColor colorWithCalibratedRed:0.61 green:0.76 blue:0.69 alpha:1.0];
}

- (NSColor *)buttonTitleColorForRole:(NSString *)role enabled:(BOOL)enabled {
    if (!enabled) {
        return [NSColor colorWithCalibratedRed:0.38 green:0.44 blue:0.41 alpha:1.0];
    }
    if ([role isEqualToString:@"primary"]) {
        return [NSColor whiteColor];
    }
    if ([role isEqualToString:@"danger"]) {
        return [NSColor colorWithCalibratedRed:0.46 green:0.16 blue:0.18 alpha:1.0];
    }
    return [NSColor colorWithCalibratedRed:0.10 green:0.32 blue:0.25 alpha:1.0];
}

- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    (void)notification;
    [self buildWindow];
    [self.window makeKeyAndOrderFront:nil];
    [NSApp activateIgnoringOtherApps:YES];
    [self startServer:nil];
}

- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender {
    (void)sender;
    return YES;
}

- (NSApplicationTerminateReply)applicationShouldTerminate:(NSApplication *)sender {
    (void)sender;
    if (self.serverTask != nil && self.serverTask.isRunning) {
        self.quitAfterShutdown = YES;
        [self shutdownServerAndRunIfNeeded];
        return NSTerminateLater;
    }
    return NSTerminateNow;
}

- (void)buildWindow {
    self.lineBuffer = [NSMutableString string];

    NSRect frame = NSMakeRect(0, 0, 720, 520);
    self.window = [[NSWindow alloc] initWithContentRect:frame
                                              styleMask:(NSWindowStyleMaskTitled |
                                                         NSWindowStyleMaskClosable |
                                                         NSWindowStyleMaskMiniaturizable)
                                                backing:NSBackingStoreBuffered
                                                  defer:NO];
    self.window.title = @"Playwright Screenshots";
    self.window.delegate = self;

    NSView *content = self.window.contentView;
    content.wantsLayer = YES;
    content.layer.backgroundColor = [[NSColor colorWithRed:0.95 green:0.96 blue:0.93 alpha:1.0] CGColor];

    NSTextField *titleLabel = [self labelWithString:@"Playwright Screenshots"
                                               font:[NSFont boldSystemFontOfSize:26]
                                              color:[NSColor colorWithCalibratedWhite:0.15 alpha:1.0]];
    NSTextField *subtitleLabel = [self labelWithString:@"Native macOS wrapper for the local web GUI. No Terminal window needed."
                                                  font:[NSFont systemFontOfSize:13]
                                                 color:[self bodyTextColor]];
    self.statusLabel = [self labelWithString:@"Starting..."
                                        font:[NSFont boldSystemFontOfSize:15]
                                       color:[NSColor colorWithCalibratedRed:0.10 green:0.32 blue:0.25 alpha:1.0]];
    self.detailLabel = [self labelWithString:@"Preparing the local GUI server."
                                        font:[NSFont systemFontOfSize:13]
                                       color:[self bodyTextColor]];
    self.urlLabel = [self labelWithString:@"Browser URL: waiting for local server..."
                                     font:[NSFont monospacedSystemFontOfSize:12 weight:NSFontWeightRegular]
                                    color:[NSColor colorWithCalibratedRed:0.24 green:0.31 blue:0.29 alpha:1.0]];
    self.urlLabel.lineBreakMode = NSLineBreakByTruncatingMiddle;

    self.startButton = [self buttonWithTitle:@"Start GUI" action:@selector(startServer:)];
    self.openButton = [self buttonWithTitle:@"Open GUI" action:@selector(openGUI:)];
    self.stopButton = [self buttonWithTitle:@"Stop GUI" action:@selector(stopServer:)];
    self.revealButton = [self buttonWithTitle:@"Open Project Folder" action:@selector(revealProjectFolder:)];

    NSScrollView *logScrollView = [[NSScrollView alloc] initWithFrame:NSZeroRect];
    logScrollView.hasVerticalScroller = YES;
    logScrollView.borderType = NSNoBorder;
    logScrollView.drawsBackground = NO;
    logScrollView.translatesAutoresizingMaskIntoConstraints = NO;

    self.logView = [[NSTextView alloc] initWithFrame:NSZeroRect];
    self.logView.editable = NO;
    self.logView.selectable = YES;
    self.logView.font = [NSFont monospacedSystemFontOfSize:12 weight:NSFontWeightRegular];
    self.logView.backgroundColor = [NSColor colorWithCalibratedRed:0.11 green:0.13 blue:0.12 alpha:1.0];
    self.logView.textColor = [NSColor colorWithCalibratedRed:0.90 green:0.94 blue:0.92 alpha:1.0];
    self.logView.textContainerInset = NSMakeSize(12, 12);
    logScrollView.documentView = self.logView;

    NSView *buttonRow = [[NSView alloc] initWithFrame:NSZeroRect];
    buttonRow.translatesAutoresizingMaskIntoConstraints = NO;

    for (NSView *view in @[titleLabel, subtitleLabel, self.statusLabel, self.detailLabel, self.urlLabel, buttonRow, logScrollView]) {
        view.translatesAutoresizingMaskIntoConstraints = NO;
        [content addSubview:view];
    }

    NSArray<NSButton *> *buttons = @[self.startButton, self.openButton, self.stopButton, self.revealButton];
    for (NSButton *button in buttons) {
        button.translatesAutoresizingMaskIntoConstraints = NO;
        [buttonRow addSubview:button];
    }

    NSDictionary<NSString *, NSView *> *views = @{
        @"title": titleLabel,
        @"subtitle": subtitleLabel,
        @"status": self.statusLabel,
        @"detail": self.detailLabel,
        @"url": self.urlLabel,
        @"buttons": buttonRow,
        @"log": logScrollView,
    };

    [NSLayoutConstraint activateConstraints:[NSLayoutConstraint constraintsWithVisualFormat:@"H:|-24-[title]-24-|"
                                                                                     options:0
                                                                                     metrics:nil
                                                                                       views:views]];
    [NSLayoutConstraint activateConstraints:[NSLayoutConstraint constraintsWithVisualFormat:@"H:|-24-[subtitle]-24-|"
                                                                                     options:0
                                                                                     metrics:nil
                                                                                       views:views]];
    [NSLayoutConstraint activateConstraints:[NSLayoutConstraint constraintsWithVisualFormat:@"H:|-24-[status]-24-|"
                                                                                     options:0
                                                                                     metrics:nil
                                                                                       views:views]];
    [NSLayoutConstraint activateConstraints:[NSLayoutConstraint constraintsWithVisualFormat:@"H:|-24-[detail]-24-|"
                                                                                     options:0
                                                                                     metrics:nil
                                                                                       views:views]];
    [NSLayoutConstraint activateConstraints:[NSLayoutConstraint constraintsWithVisualFormat:@"H:|-24-[url]-24-|"
                                                                                     options:0
                                                                                     metrics:nil
                                                                                       views:views]];
    [NSLayoutConstraint activateConstraints:[NSLayoutConstraint constraintsWithVisualFormat:@"H:|-24-[buttons]-24-|"
                                                                                     options:0
                                                                                     metrics:nil
                                                                                       views:views]];
    [NSLayoutConstraint activateConstraints:[NSLayoutConstraint constraintsWithVisualFormat:@"H:|-24-[log]-24-|"
                                                                                     options:0
                                                                                     metrics:nil
                                                                                       views:views]];
    [NSLayoutConstraint activateConstraints:[NSLayoutConstraint constraintsWithVisualFormat:@"V:|-24-[title]-4-[subtitle]-18-[status]-4-[detail]-10-[url]-18-[buttons(32)]-18-[log]-24-|"
                                                                                     options:0
                                                                                     metrics:nil
                                                                                       views:views]];

    NSDictionary<NSString *, NSButton *> *buttonViews = @{
        @"start": self.startButton,
        @"open": self.openButton,
        @"stop": self.stopButton,
        @"reveal": self.revealButton,
    };
    [NSLayoutConstraint activateConstraints:[NSLayoutConstraint constraintsWithVisualFormat:@"H:|[start(118)]-12-[open(118)]-12-[stop(118)]-12-[reveal(170)]"
                                                                                     options:NSLayoutFormatAlignAllCenterY
                                                                                     metrics:nil
                                                                                       views:buttonViews]];
    [NSLayoutConstraint activateConstraints:[NSLayoutConstraint constraintsWithVisualFormat:@"V:|[start]|"
                                                                                     options:0
                                                                                     metrics:nil
                                                                                       views:buttonViews]];

    [self updateButtons];
    [self appendLog:@"Launcher ready.\n"];
}

- (NSTextField *)labelWithString:(NSString *)string font:(NSFont *)font color:(NSColor *)color {
    NSTextField *label = [[NSTextField alloc] initWithFrame:NSZeroRect];
    label.stringValue = string;
    label.bezeled = NO;
    label.drawsBackground = NO;
    label.editable = NO;
    label.selectable = NO;
    label.font = font;
    label.textColor = color;
    return label;
}

- (NSButton *)buttonWithTitle:(NSString *)title action:(SEL)action {
    NSButton *button = [NSButton buttonWithTitle:title target:self action:action];
    button.bordered = NO;
    button.buttonType = NSButtonTypeMomentaryPushIn;
    button.wantsLayer = YES;
    button.layer.cornerRadius = 9.0;
    button.layer.borderWidth = 1.0;
    button.font = [NSFont systemFontOfSize:13 weight:NSFontWeightSemibold];
    return button;
}

- (void)applyStyleToButton:(NSButton *)button role:(NSString *)role enabled:(BOOL)enabled {
    button.enabled = enabled;
    button.alphaValue = 1.0;
    button.layer.backgroundColor = [self buttonBackgroundColorForRole:role enabled:enabled].CGColor;
    button.layer.borderColor = [self buttonBorderColorForRole:role enabled:enabled].CGColor;

    NSDictionary<NSAttributedStringKey, id> *attributes = @{
        NSForegroundColorAttributeName: [self buttonTitleColorForRole:role enabled:enabled],
        NSFontAttributeName: button.font ?: [NSFont systemFontOfSize:13 weight:NSFontWeightSemibold],
    };
    NSAttributedString *styledTitle = [[NSAttributedString alloc] initWithString:button.title attributes:attributes];
    button.attributedTitle = styledTitle;
    button.attributedAlternateTitle = styledTitle;
}

- (NSURL *)projectRootURL {
    NSURL *candidate = [[NSBundle mainBundle].bundleURL URLByDeletingLastPathComponent];
    NSFileManager *fileManager = [NSFileManager defaultManager];

    while (candidate != nil) {
        NSURL *pythonURL = [candidate URLByAppendingPathComponent:@".venv/bin/python"];
        NSURL *guiURL = [candidate URLByAppendingPathComponent:@"gui.py"];
        if ([fileManager isExecutableFileAtPath:pythonURL.path] &&
            [fileManager fileExistsAtPath:guiURL.path]) {
            return candidate;
        }

        NSURL *nextCandidate = [candidate URLByDeletingLastPathComponent];
        if ([nextCandidate.path isEqualToString:candidate.path]) {
            break;
        }
        candidate = nextCandidate;
    }

    return [[NSBundle mainBundle].bundleURL URLByDeletingLastPathComponent];
}

- (NSURL *)pythonURL {
    return [[self projectRootURL] URLByAppendingPathComponent:@".venv/bin/python"];
}

- (NSURL *)guiScriptURL {
    return [[self projectRootURL] URLByAppendingPathComponent:@"gui.py"];
}

- (void)startServer:(id)sender {
    (void)sender;
    if (self.serverTask != nil && self.serverTask.isRunning) {
        [self openGUI:nil];
        return;
    }

    NSURL *pythonURL = [self pythonURL];
    NSURL *guiURL = [self guiScriptURL];
    if (![[NSFileManager defaultManager] isExecutableFileAtPath:pythonURL.path]) {
        [self setStatus:@"Missing Python"
                 detail:[NSString stringWithFormat:@"Expected virtual environment Python at %@", pythonURL.path]];
        [self appendLog:[NSString stringWithFormat:@"Missing Python executable: %@\n", pythonURL.path]];
        return;
    }
    if (![[NSFileManager defaultManager] fileExistsAtPath:guiURL.path]) {
        [self setStatus:@"Missing gui.py"
                 detail:[NSString stringWithFormat:@"Expected gui.py at %@", guiURL.path]];
        [self appendLog:[NSString stringWithFormat:@"Missing gui.py: %@\n", guiURL.path]];
        return;
    }

    self.serverURL = nil;
    self.browserOpenedAutomatically = NO;
    [self.lineBuffer setString:@""];
    [self setStatus:@"Starting"
             detail:@"Launching the local GUI server..."];
    self.urlLabel.stringValue = @"Browser URL: waiting for local server...";
    [self appendLog:[NSString stringWithFormat:@"Starting %@ -u %@ --no-browser-open\n", pythonURL.path, guiURL.path]];

    self.serverTask = [[NSTask alloc] init];
    self.serverTask.currentDirectoryURL = [self projectRootURL];
    self.serverTask.executableURL = pythonURL;
    self.serverTask.arguments = @[@"-u", guiURL.path, @"--no-browser-open"];
    self.serverTask.standardInput = [NSFileHandle fileHandleForReadingAtPath:@"/dev/null"];
    self.outputPipe = [NSPipe pipe];
    self.serverTask.standardOutput = self.outputPipe;
    self.serverTask.standardError = self.outputPipe;

    __weak typeof(self) weakSelf = self;
    self.outputPipe.fileHandleForReading.readabilityHandler = ^(NSFileHandle *handle) {
        NSData *data = handle.availableData;
        if (data.length == 0) {
            handle.readabilityHandler = nil;
            return;
        }
        NSString *text = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
        if (text.length == 0) {
            return;
        }
        dispatch_async(dispatch_get_main_queue(), ^{
            [weakSelf consumeOutput:text];
        });
    };

    self.serverTask.terminationHandler = ^(NSTask *task) {
        dispatch_async(dispatch_get_main_queue(), ^{
            [weakSelf serverTaskDidTerminate:task];
        });
    };

    NSError *error = nil;
    if (![self.serverTask launchAndReturnError:&error]) {
        [self setStatus:@"Failed to start"
                 detail:error.localizedDescription ?: @"Could not launch the local GUI server."];
        [self appendLog:[NSString stringWithFormat:@"Launch failed: %@\n", error.localizedDescription ?: @"Unknown error"]];
        self.serverTask = nil;
        self.outputPipe = nil;
        [self updateButtons];
        return;
    }

    [self updateButtons];
}

- (void)consumeOutput:(NSString *)text {
    [self appendLog:text];
    [self.lineBuffer appendString:text];

    while (YES) {
        NSRange newlineRange = [self.lineBuffer rangeOfString:@"\n"];
        if (newlineRange.location == NSNotFound) {
            break;
        }
        NSString *line = [self.lineBuffer substringToIndex:newlineRange.location];
        [self.lineBuffer deleteCharactersInRange:NSMakeRange(0, newlineRange.location + newlineRange.length)];
        [self handleLogLine:line];
    }
}

- (void)handleLogLine:(NSString *)line {
    NSString *prefix = @"Opening local GUI at ";
    if (![line hasPrefix:prefix]) {
        return;
    }

    NSString *urlString = [[line substringFromIndex:prefix.length] stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceAndNewlineCharacterSet]];
    NSURL *url = [NSURL URLWithString:urlString];
    if (url == nil) {
        return;
    }

    self.serverURL = url;
    [self setStatus:@"Running"
             detail:@"The local GUI server is active. Your browser should open automatically."];
    self.urlLabel.stringValue = [NSString stringWithFormat:@"Browser URL: %@", url.absoluteString];
    [self updateButtons];

    if (!self.browserOpenedAutomatically) {
        self.browserOpenedAutomatically = YES;
        [self openGUI:nil];
    }
}

- (void)serverTaskDidTerminate:(NSTask *)task {
    (void)task;
    self.outputPipe.fileHandleForReading.readabilityHandler = nil;
    int status = self.serverTask.terminationStatus;
    self.serverTask = nil;
    self.outputPipe = nil;
    self.browserOpenedAutomatically = NO;

    if (self.quitAfterShutdown) {
        [NSApp replyToApplicationShouldTerminate:YES];
        return;
    }

    if (status == 0 || status == SIGTERM || status == SIGINT) {
        [self setStatus:@"Stopped"
                 detail:@"The local GUI server is not running."];
    } else {
        [self setStatus:@"Stopped"
                 detail:[NSString stringWithFormat:@"The local GUI server ended with status %d.", status]];
    }
    [self updateButtons];
}

- (void)openGUI:(id)sender {
    (void)sender;
    if (self.serverURL == nil) {
        return;
    }
    [[NSWorkspace sharedWorkspace] openURL:self.serverURL];
}

- (void)revealProjectFolder:(id)sender {
    (void)sender;
    [[NSWorkspace sharedWorkspace] openURL:[self projectRootURL]];
}

- (void)stopServer:(id)sender {
    (void)sender;
    [self shutdownServerAndRunIfNeeded];
}

- (void)shutdownServerAndRunIfNeeded {
    if (self.serverTask == nil || !self.serverTask.isRunning) {
        [self setStatus:@"Stopped"
                 detail:@"The local GUI server is not running."];
        [self updateButtons];
        if (self.quitAfterShutdown) {
            [NSApp replyToApplicationShouldTerminate:YES];
        }
        return;
    }

    [self setStatus:@"Stopping"
             detail:@"Stopping the local GUI server and any active run..."];
    [self appendLog:@"Stopping local GUI server...\n"];

    NSURL *stopURL = nil;
    if (self.serverURL != nil) {
        stopURL = [self.serverURL URLByAppendingPathComponent:@"api/stop"];
    }
    if (stopURL != nil) {
        NSMutableURLRequest *request = [NSMutableURLRequest requestWithURL:stopURL];
        request.HTTPMethod = @"POST";
        request.timeoutInterval = 2.0;
        request.HTTPBody = [@"{}" dataUsingEncoding:NSUTF8StringEncoding];
        [request setValue:@"application/json" forHTTPHeaderField:@"Content-Type"];
        [[[NSURLSession sharedSession] dataTaskWithRequest:request] resume];
    }

    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(0.8 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
        if (self.serverTask == nil || !self.serverTask.isRunning) {
            return;
        }
        [self.serverTask interrupt];
        [self scheduleForceStop];
    });
}

- (void)scheduleForceStop {
    pid_t pid = self.serverTask.processIdentifier;
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(5.0 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
        if (self.serverTask == nil || !self.serverTask.isRunning) {
            return;
        }
        kill(pid, SIGTERM);
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(2.0 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
            if (self.serverTask == nil || !self.serverTask.isRunning) {
                return;
            }
            kill(pid, SIGKILL);
        });
    });
}

- (void)setStatus:(NSString *)status detail:(NSString *)detail {
    self.statusLabel.stringValue = status;
    self.detailLabel.stringValue = detail;
}

- (void)updateButtons {
    BOOL running = (self.serverTask != nil && self.serverTask.isRunning);
    self.startButton.title = running ? @"GUI Running" : @"Start GUI";
    self.openButton.title = @"Open GUI";
    self.stopButton.title = @"Stop GUI";
    self.revealButton.title = @"Open Project Folder";
    [self applyStyleToButton:self.startButton role:@"primary" enabled:!running];
    [self applyStyleToButton:self.openButton role:@"secondary" enabled:(self.serverURL != nil)];
    [self applyStyleToButton:self.stopButton role:@"danger" enabled:running];
    [self applyStyleToButton:self.revealButton role:@"secondary" enabled:YES];
}

- (void)appendLog:(NSString *)text {
    if (text.length == 0) {
        return;
    }
    NSAttributedString *chunk = [[NSAttributedString alloc] initWithString:text attributes:@{
        NSForegroundColorAttributeName: self.logView.textColor ?: NSColor.textColor,
        NSFontAttributeName: self.logView.font ?: [NSFont monospacedSystemFontOfSize:12 weight:NSFontWeightRegular],
    }];
    [[self.logView textStorage] appendAttributedString:chunk];

    NSString *fullText = self.logView.string ?: @"";
    if (fullText.length > 12000) {
        NSString *trimmed = [fullText substringFromIndex:fullText.length - 12000];
        [self.logView.textStorage setAttributedString:[[NSAttributedString alloc] initWithString:trimmed attributes:@{
            NSForegroundColorAttributeName: self.logView.textColor ?: NSColor.textColor,
            NSFontAttributeName: self.logView.font ?: [NSFont monospacedSystemFontOfSize:12 weight:NSFontWeightRegular],
        }]];
    }
    [self.logView scrollRangeToVisible:NSMakeRange(self.logView.string.length, 0)];
}

@end

int main(int argc, const char *argv[]) {
    (void)argc;
    (void)argv;
    @autoreleasepool {
        NSApplication *application = [NSApplication sharedApplication];
        AppController *delegate = [[AppController alloc] init];
        application.delegate = delegate;
        [application setActivationPolicy:NSApplicationActivationPolicyRegular];
        return NSApplicationMain(argc, argv);
    }
}
