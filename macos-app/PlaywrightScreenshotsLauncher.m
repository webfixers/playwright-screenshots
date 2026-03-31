#import <Cocoa/Cocoa.h>
#import <signal.h>

static NSString *const kEventPrefix = @"EVENT_JSON:";

@interface AppController : NSObject <NSApplicationDelegate, NSWindowDelegate>
@property(nonatomic, strong) NSWindow *window;
@property(nonatomic, strong) NSTextField *statusLabel;
@property(nonatomic, strong) NSTextField *detailLabel;
@property(nonatomic, strong) NSTextField *progressLabel;
@property(nonatomic, strong) NSTextField *outputLabel;
@property(nonatomic, strong) NSTextField *versionLabel;
@property(nonatomic, strong) NSTextField *inputPromptLabel;
@property(nonatomic, strong) NSTextField *urlField;
@property(nonatomic, strong) NSTextField *includeField;
@property(nonatomic, strong) NSTextField *excludeField;
@property(nonatomic, strong) NSTextField *maxUrlsField;
@property(nonatomic, strong) NSPopUpButton *inputModePopup;
@property(nonatomic, strong) NSPopUpButton *variantPopup;
@property(nonatomic, strong) NSPopUpButton *timeoutPopup;
@property(nonatomic, strong) NSButton *onlyFailedButton;
@property(nonatomic, strong) NSButton *generateIndexButton;
@property(nonatomic, strong) NSButton *blockMediaButton;
@property(nonatomic, strong) NSButton *startButton;
@property(nonatomic, strong) NSButton *pauseButton;
@property(nonatomic, strong) NSButton *stopButton;
@property(nonatomic, strong) NSButton *openOutputButton;
@property(nonatomic, strong) NSButton *chooseFileButton;
@property(nonatomic, strong) NSButton *revealButton;
@property(nonatomic, strong) NSButton *quitButton;
@property(nonatomic, strong) NSPopUpButton *historyPopup;
@property(nonatomic, strong) NSButton *openHistoryButton;
@property(nonatomic, strong) NSTextView *logView;
@property(nonatomic, strong) NSTask *runTask;
@property(nonatomic, strong) NSPipe *outputPipe;
@property(nonatomic, strong) NSMutableString *lineBuffer;
@property(nonatomic, strong) NSURL *lastOutputURL;
@property(nonatomic, strong) NSURL *selectedFileURL;
@property(nonatomic, strong) NSMutableArray<NSDictionary *> *recentRuns;
@property(nonatomic, assign) BOOL quitAfterShutdown;
@property(nonatomic, assign) BOOL stopRequested;
@property(nonatomic, assign) BOOL paused;
@property(nonatomic, assign) NSInteger currentPageIndex;
@property(nonatomic, assign) NSInteger totalPages;
@property(nonatomic, assign) NSInteger pagesCompleted;
@property(nonatomic, copy) NSString *currentRunLabel;
@property(nonatomic, copy) NSString *runStartedAt;
@end

@implementation AppController

- (BOOL)isDarkAppearance {
    if (self.window == nil) {
        return NO;
    }
    NSAppearanceName bestMatch = [self.window.effectiveAppearance bestMatchFromAppearancesWithNames:@[
        NSAppearanceNameAqua,
        NSAppearanceNameDarkAqua
    ]];
    return [bestMatch isEqualToString:NSAppearanceNameDarkAqua];
}

- (NSColor *)windowBackgroundColor {
    return [NSColor windowBackgroundColor];
}

- (NSColor *)bodyTextColor {
    return [NSColor labelColor];
}

- (NSColor *)mutedTextColor {
    return [NSColor secondaryLabelColor];
}

- (NSColor *)buttonBackgroundColorForRole:(NSString *)role enabled:(BOOL)enabled {
    BOOL isDark = [self isDarkAppearance];
    if (!enabled) {
        return isDark
            ? [NSColor colorWithCalibratedRed:0.20 green:0.22 blue:0.21 alpha:1.0]
            : [NSColor colorWithCalibratedRed:0.91 green:0.92 blue:0.90 alpha:1.0];
    }
    if ([role isEqualToString:@"primary"]) {
        return isDark
            ? [NSColor colorWithCalibratedRed:0.18 green:0.53 blue:0.42 alpha:1.0]
            : [NSColor colorWithCalibratedRed:0.10 green:0.38 blue:0.30 alpha:1.0];
    }
    if ([role isEqualToString:@"danger"]) {
        return isDark
            ? [NSColor colorWithCalibratedRed:0.34 green:0.19 blue:0.20 alpha:1.0]
            : [NSColor colorWithCalibratedRed:0.95 green:0.89 blue:0.89 alpha:1.0];
    }
    return isDark
        ? [NSColor colorWithCalibratedRed:0.18 green:0.24 blue:0.22 alpha:1.0]
        : [NSColor colorWithCalibratedRed:0.90 green:0.95 blue:0.92 alpha:1.0];
}

- (NSColor *)buttonBorderColorForRole:(NSString *)role enabled:(BOOL)enabled {
    BOOL isDark = [self isDarkAppearance];
    if (!enabled) {
        return isDark
            ? [NSColor colorWithCalibratedRed:0.35 green:0.39 blue:0.37 alpha:1.0]
            : [NSColor colorWithCalibratedRed:0.71 green:0.75 blue:0.71 alpha:1.0];
    }
    if ([role isEqualToString:@"primary"]) {
        return isDark
            ? [NSColor colorWithCalibratedRed:0.29 green:0.67 blue:0.54 alpha:1.0]
            : [NSColor colorWithCalibratedRed:0.10 green:0.38 blue:0.30 alpha:1.0];
    }
    if ([role isEqualToString:@"danger"]) {
        return isDark
            ? [NSColor colorWithCalibratedRed:0.72 green:0.44 blue:0.45 alpha:1.0]
            : [NSColor colorWithCalibratedRed:0.78 green:0.55 blue:0.55 alpha:1.0];
    }
    return isDark
        ? [NSColor colorWithCalibratedRed:0.41 green:0.58 blue:0.52 alpha:1.0]
        : [NSColor colorWithCalibratedRed:0.61 green:0.76 blue:0.69 alpha:1.0];
}

- (NSColor *)buttonTitleColorForRole:(NSString *)role enabled:(BOOL)enabled {
    BOOL isDark = [self isDarkAppearance];
    if (!enabled) {
        return isDark
            ? [NSColor colorWithCalibratedRed:0.60 green:0.65 blue:0.63 alpha:1.0]
            : [NSColor colorWithCalibratedRed:0.38 green:0.44 blue:0.41 alpha:1.0];
    }
    if ([role isEqualToString:@"primary"]) {
        return [NSColor whiteColor];
    }
    if ([role isEqualToString:@"danger"]) {
        return isDark
            ? [NSColor colorWithCalibratedRed:0.97 green:0.78 blue:0.78 alpha:1.0]
            : [NSColor colorWithCalibratedRed:0.46 green:0.16 blue:0.18 alpha:1.0];
    }
    return isDark
        ? [NSColor colorWithCalibratedRed:0.78 green:0.92 blue:0.86 alpha:1.0]
        : [NSColor colorWithCalibratedRed:0.10 green:0.32 blue:0.25 alpha:1.0];
}

- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    (void)notification;
    [self buildMainMenu];
    [self buildWindow];
    [self.window makeKeyAndOrderFront:nil];
    [NSApp activateIgnoringOtherApps:YES];
}

- (void)buildMainMenu {
    NSMenu *mainMenu = [[NSMenu alloc] initWithTitle:@""];

    NSMenuItem *appMenuItem = [[NSMenuItem alloc] initWithTitle:@"" action:nil keyEquivalent:@""];
    [mainMenu addItem:appMenuItem];

    NSMenu *appMenu = [[NSMenu alloc] initWithTitle:@"Playwright Screenshots"];
    NSString *appName = [NSRunningApplication currentApplication].localizedName ?: @"Playwright Screenshots";
    NSMenuItem *quitItem = [[NSMenuItem alloc] initWithTitle:[NSString stringWithFormat:@"Quit %@", appName]
                                                      action:@selector(terminate:)
                                               keyEquivalent:@"q"];
    [appMenu addItem:quitItem];
    appMenuItem.submenu = appMenu;

    NSMenuItem *editMenuItem = [[NSMenuItem alloc] initWithTitle:@"" action:nil keyEquivalent:@""];
    [mainMenu addItem:editMenuItem];

    NSMenu *editMenu = [[NSMenu alloc] initWithTitle:@"Edit"];
    NSArray<NSMenuItem *> *editItems = @[
        [[NSMenuItem alloc] initWithTitle:@"Undo" action:@selector(undo:) keyEquivalent:@"z"],
        [[NSMenuItem alloc] initWithTitle:@"Redo" action:@selector(redo:) keyEquivalent:@"Z"],
        [NSMenuItem separatorItem],
        [[NSMenuItem alloc] initWithTitle:@"Cut" action:@selector(cut:) keyEquivalent:@"x"],
        [[NSMenuItem alloc] initWithTitle:@"Copy" action:@selector(copy:) keyEquivalent:@"c"],
        [[NSMenuItem alloc] initWithTitle:@"Paste" action:@selector(paste:) keyEquivalent:@"v"],
        [[NSMenuItem alloc] initWithTitle:@"Select All" action:@selector(selectAll:) keyEquivalent:@"a"],
    ];
    for (NSMenuItem *item in editItems) {
        [editMenu addItem:item];
    }
    editMenuItem.submenu = editMenu;

    [NSApp setMainMenu:mainMenu];
}

- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender {
    (void)sender;
    return YES;
}

- (NSApplicationTerminateReply)applicationShouldTerminate:(NSApplication *)sender {
    (void)sender;
    if (self.runTask != nil && self.runTask.isRunning) {
        self.quitAfterShutdown = YES;
        [self stopRun:nil];
        return NSTerminateLater;
    }
    return NSTerminateNow;
}

- (NSTextField *)labelWithString:(NSString *)string font:(NSFont *)font color:(NSColor *)color frame:(NSRect)frame {
    NSTextField *label = [[NSTextField alloc] initWithFrame:frame];
    label.stringValue = string;
    label.bezeled = NO;
    label.drawsBackground = NO;
    label.editable = NO;
    label.selectable = NO;
    label.font = font;
    label.textColor = color;
    return label;
}

- (NSTextField *)inputFieldWithFrame:(NSRect)frame placeholder:(NSString *)placeholder {
    NSTextField *field = [[NSTextField alloc] initWithFrame:frame];
    field.font = [NSFont systemFontOfSize:13];
    field.placeholderString = placeholder;
    field.bezelStyle = NSTextFieldRoundedBezel;
    field.textColor = [NSColor textColor];
    field.backgroundColor = [NSColor textBackgroundColor];
    field.drawsBackground = YES;
    field.bordered = YES;
    field.focusRingType = NSFocusRingTypeDefault;
    NSAttributedString *styledPlaceholder = [[NSAttributedString alloc] initWithString:placeholder attributes:@{
        NSForegroundColorAttributeName: [self mutedTextColor],
        NSFontAttributeName: field.font ?: [NSFont systemFontOfSize:13],
    }];
    field.placeholderAttributedString = styledPlaceholder;
    return field;
}

- (NSPopUpButton *)popupWithItems:(NSArray<NSString *> *)items frame:(NSRect)frame {
    NSPopUpButton *popup = [[NSPopUpButton alloc] initWithFrame:frame pullsDown:NO];
    popup.font = [NSFont systemFontOfSize:13];
    if ([popup respondsToSelector:@selector(setContentTintColor:)]) {
        popup.contentTintColor = [self bodyTextColor];
    }
    [popup addItemsWithTitles:items];
    NSDictionary<NSAttributedStringKey, id> *attributes = @{
        NSForegroundColorAttributeName: [self bodyTextColor],
        NSFontAttributeName: popup.font ?: [NSFont systemFontOfSize:13],
    };
    for (NSMenuItem *item in popup.itemArray) {
        item.attributedTitle = [[NSAttributedString alloc] initWithString:item.title attributes:attributes];
    }
    return popup;
}

- (NSButton *)checkboxWithTitle:(NSString *)title frame:(NSRect)frame {
    NSButton *checkbox = [[NSButton alloc] initWithFrame:frame];
    checkbox.buttonType = NSButtonTypeSwitch;
    checkbox.title = title;
    checkbox.font = [NSFont systemFontOfSize:13];
    checkbox.attributedTitle = [[NSAttributedString alloc] initWithString:title attributes:@{
        NSForegroundColorAttributeName: [self bodyTextColor],
        NSFontAttributeName: checkbox.font ?: [NSFont systemFontOfSize:13],
    }];
    return checkbox;
}

- (NSButton *)buttonWithTitle:(NSString *)title action:(SEL)action frame:(NSRect)frame {
    NSButton *button = [NSButton buttonWithTitle:title target:self action:action];
    button.frame = frame;
    button.bordered = NO;
    button.buttonType = NSButtonTypeMomentaryPushIn;
    button.wantsLayer = YES;
    button.layer.cornerRadius = 9.0;
    button.layer.borderWidth = 1.0;
    button.font = [NSFont systemFontOfSize:13 weight:NSFontWeightSemibold];
    return button;
}

- (NSURL *)historyFileURL {
    return [[self projectRootURL] URLByAppendingPathComponent:@".native-app-history.json"];
}

- (NSMutableArray<NSDictionary *> *)loadHistory {
    NSData *data = [NSData dataWithContentsOfURL:[self historyFileURL]];
    if (data == nil) {
        return [NSMutableArray array];
    }
    NSError *error = nil;
    id parsed = [NSJSONSerialization JSONObjectWithData:data options:0 error:&error];
    if (![parsed isKindOfClass:[NSArray class]] || error != nil) {
        return [NSMutableArray array];
    }
    NSMutableArray<NSDictionary *> *entries = [NSMutableArray array];
    for (id item in (NSArray *)parsed) {
        if ([item isKindOfClass:[NSDictionary class]]) {
            [entries addObject:item];
        }
    }
    return entries;
}

- (void)saveHistory {
    NSError *error = nil;
    NSData *data = [NSJSONSerialization dataWithJSONObject:self.recentRuns ?: @[] options:NSJSONWritingPrettyPrinted error:&error];
    if (data == nil || error != nil) {
        return;
    }
    [data writeToURL:[self historyFileURL] atomically:YES];
}

- (void)refreshHistoryControls {
    [self.historyPopup removeAllItems];
    if (self.recentRuns.count == 0) {
        [self.historyPopup addItemWithTitle:@"No recent runs yet"];
        self.historyPopup.enabled = NO;
        return;
    }
    NSDateFormatter *formatter = [[NSDateFormatter alloc] init];
    formatter.dateFormat = @"yyyy-MM-dd HH:mm:ss";
    for (NSDictionary *entry in self.recentRuns) {
        NSString *label = entry[@"label"] ?: @"Run";
        NSString *status = entry[@"status"] ?: @"unknown";
        NSString *startedAt = entry[@"started_at"] ?: @"";
        NSString *title = startedAt.length > 0
            ? [NSString stringWithFormat:@"%@ • %@ • %@", label, status, startedAt]
            : [NSString stringWithFormat:@"%@ • %@", label, status];
        [self.historyPopup addItemWithTitle:title];
    }
    self.historyPopup.enabled = YES;
}

- (NSString *)inputModeKey {
    NSString *selected = self.inputModePopup.selectedItem.title ?: @"Single website";
    return [selected hasPrefix:@"Website list"] ? @"file" : @"single";
}

- (void)updateInputModeUI {
    BOOL fileMode = [[self inputModeKey] isEqualToString:@"file"];
    self.inputPromptLabel.stringValue = fileMode ? @"Website list file" : @"Website or sitemap";
    NSString *placeholder = fileMode ? @"/path/to/sites.txt" : @"https://example.com or example.com/sitemap.xml";
    self.urlField.placeholderString = placeholder;
    self.urlField.placeholderAttributedString = [[NSAttributedString alloc] initWithString:placeholder attributes:@{
        NSForegroundColorAttributeName: [self mutedTextColor],
        NSFontAttributeName: self.urlField.font ?: [NSFont systemFontOfSize:13],
    }];
    self.chooseFileButton.hidden = !fileMode;
    self.chooseFileButton.enabled = fileMode;
    if (!fileMode && self.selectedFileURL != nil && self.urlField.stringValue.length == 0) {
        self.selectedFileURL = nil;
    }
    [self updateButtons];
}

- (void)inputModeChanged:(id)sender {
    (void)sender;
    [self updateInputModeUI];
}

- (void)chooseInputFile:(id)sender {
    (void)sender;
    NSOpenPanel *panel = [NSOpenPanel openPanel];
    panel.canChooseFiles = YES;
    panel.canChooseDirectories = NO;
    panel.allowsMultipleSelection = NO;
    panel.prompt = @"Choose file";
    panel.message = @"Choose a text file with one website or sitemap per line.";
    if ([panel runModal] == NSModalResponseOK) {
        self.selectedFileURL = panel.URL;
        self.urlField.stringValue = panel.URL.path ?: @"";
    }
}

- (void)openSelectedHistory:(id)sender {
    (void)sender;
    if (self.recentRuns.count == 0) {
        return;
    }
    NSInteger index = self.historyPopup.indexOfSelectedItem;
    if (index < 0 || index >= (NSInteger)self.recentRuns.count) {
        return;
    }
    NSDictionary *entry = self.recentRuns[(NSUInteger)index];
    NSString *path = entry[@"output_path"] ?: @"";
    if (path.length == 0) {
        return;
    }
    [[NSWorkspace sharedWorkspace] openURL:[NSURL fileURLWithPath:path]];
}

- (void)applyStyleToButton:(NSButton *)button role:(NSString *)role enabled:(BOOL)enabled {
    button.enabled = YES;
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

- (void)buildWindow {
    self.lineBuffer = [NSMutableString string];
    self.recentRuns = [self loadHistory];

    NSRect frame = NSMakeRect(0, 0, 860, 860);
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
    content.layer.backgroundColor = [self windowBackgroundColor].CGColor;

    CGFloat left = 24.0;
    CGFloat width = frame.size.width;

    NSTextField *titleLabel = [self labelWithString:@"Playwright Screenshots"
                                               font:[NSFont boldSystemFontOfSize:30]
                                              color:[NSColor colorWithCalibratedWhite:0.15 alpha:1.0]
                                              frame:NSMakeRect(left, 790, width - 48, 36)];
    NSTextField *subtitleLabel = [self labelWithString:@"Native macOS app for running Playwright screenshot jobs without a browser or Terminal window."
                                                  font:[NSFont systemFontOfSize:13]
                                                 color:[self bodyTextColor]
                                                 frame:NSMakeRect(left, 766, width - 48, 18)];

    NSTextField *inputModePrompt = [self labelWithString:@"Input mode"
                                                    font:[NSFont systemFontOfSize:12 weight:NSFontWeightSemibold]
                                                   color:[self bodyTextColor]
                                                   frame:NSMakeRect(left, 724, 120, 18)];
    self.inputModePopup = [self popupWithItems:@[@"Single website", @"Website list file"] frame:NSMakeRect(left, 692, 180, 28)];
    self.inputModePopup.target = self;
    self.inputModePopup.action = @selector(inputModeChanged:);

    self.inputPromptLabel = [self labelWithString:@"Website or sitemap"
                                              font:[NSFont systemFontOfSize:12 weight:NSFontWeightSemibold]
                                             color:[self bodyTextColor]
                                             frame:NSMakeRect(left, 652, 240, 18)];
    self.urlField = [self inputFieldWithFrame:NSMakeRect(left, 620, width - 48 - 110, 28)
                                   placeholder:@"https://example.com or example.com/sitemap.xml"];
    self.chooseFileButton = [self buttonWithTitle:@"Choose File" action:@selector(chooseInputFile:) frame:NSMakeRect(width - 24 - 98, 620, 98, 28)];

    NSTextField *variantPrompt = [self labelWithString:@"Variant"
                                                  font:[NSFont systemFontOfSize:12 weight:NSFontWeightSemibold]
                                                 color:[self bodyTextColor]
                                                 frame:NSMakeRect(left, 580, 120, 18)];
    self.variantPopup = [self popupWithItems:@[@"basic", @"extended"] frame:NSMakeRect(left, 548, 180, 28)];

    NSTextField *timeoutPrompt = [self labelWithString:@"Timeout profile"
                                                  font:[NSFont systemFontOfSize:12 weight:NSFontWeightSemibold]
                                                 color:[self bodyTextColor]
                                                 frame:NSMakeRect(232, 580, 140, 18)];
    self.timeoutPopup = [self popupWithItems:@[@"normal", @"slow"] frame:NSMakeRect(232, 548, 180, 28)];

    NSTextField *maxPrompt = [self labelWithString:@"Max URLs"
                                              font:[NSFont systemFontOfSize:12 weight:NSFontWeightSemibold]
                                             color:[self bodyTextColor]
                                             frame:NSMakeRect(440, 580, 120, 18)];
    self.maxUrlsField = [self inputFieldWithFrame:NSMakeRect(440, 548, 110, 28) placeholder:@"Optional"];

    NSTextField *includePrompt = [self labelWithString:@"Include filters"
                                                  font:[NSFont systemFontOfSize:12 weight:NSFontWeightSemibold]
                                                 color:[self bodyTextColor]
                                                 frame:NSMakeRect(left, 508, 140, 18)];
    self.includeField = [self inputFieldWithFrame:NSMakeRect(left, 476, 388, 28)
                                       placeholder:@"/blog/,/news/"];

    NSTextField *excludePrompt = [self labelWithString:@"Exclude filters"
                                                  font:[NSFont systemFontOfSize:12 weight:NSFontWeightSemibold]
                                                 color:[self bodyTextColor]
                                                 frame:NSMakeRect(424, 508, 140, 18)];
    self.excludeField = [self inputFieldWithFrame:NSMakeRect(424, 476, 412, 28)
                                       placeholder:@"/tag/,/author/"];

    self.onlyFailedButton = [self checkboxWithTitle:@"Only failed" frame:NSMakeRect(left, 438, 120, 18)];
    self.generateIndexButton = [self checkboxWithTitle:@"Generate HTML index" frame:NSMakeRect(152, 438, 170, 18)];
    self.blockMediaButton = [self checkboxWithTitle:@"Block third-party media" frame:NSMakeRect(334, 438, 190, 18)];
    self.generateIndexButton.state = NSControlStateValueOn;

    self.startButton = [self buttonWithTitle:@"Start Run" action:@selector(startRun:) frame:NSMakeRect(left, 394, 118, 32)];
    self.pauseButton = [self buttonWithTitle:@"Pause Run" action:@selector(togglePauseRun:) frame:NSMakeRect(154, 394, 118, 32)];
    self.stopButton = [self buttonWithTitle:@"Stop Run" action:@selector(stopRun:) frame:NSMakeRect(284, 394, 118, 32)];
    self.openOutputButton = [self buttonWithTitle:@"Open Last Output" action:@selector(openLastOutput:) frame:NSMakeRect(414, 394, 140, 32)];
    self.revealButton = [self buttonWithTitle:@"Open Project Folder" action:@selector(revealProjectFolder:) frame:NSMakeRect(566, 394, 170, 32)];
    self.quitButton = [self buttonWithTitle:@"Quit App" action:@selector(quitApp:) frame:NSMakeRect(width - 24 - 118, 24, 118, 32)];

    self.statusLabel = [self labelWithString:@"Ready"
                                        font:[NSFont boldSystemFontOfSize:18]
                                       color:[NSColor colorWithCalibratedRed:0.10 green:0.32 blue:0.25 alpha:1.0]
                                       frame:NSMakeRect(left, 350, 240, 22)];
    self.detailLabel = [self labelWithString:@"Fill in a website or sitemap above to start a native screenshot run."
                                        font:[NSFont systemFontOfSize:13]
                                       color:[self bodyTextColor]
                                       frame:NSMakeRect(left, 328, width - 48, 18)];
    self.progressLabel = [self labelWithString:@"No active run."
                                          font:[NSFont systemFontOfSize:13]
                                         color:[self bodyTextColor]
                                         frame:NSMakeRect(left, 304, width - 48, 18)];
    self.outputLabel = [self labelWithString:@"Last output: not available yet."
                                        font:[NSFont monospacedSystemFontOfSize:11 weight:NSFontWeightRegular]
                                       color:[self mutedTextColor]
                                       frame:NSMakeRect(left, 282, width - 48, 18)];
    self.outputLabel.lineBreakMode = NSLineBreakByTruncatingMiddle;

    NSTextField *historyLabel = [self labelWithString:@"Recent runs"
                                                 font:[NSFont systemFontOfSize:12 weight:NSFontWeightSemibold]
                                                color:[self bodyTextColor]
                                                frame:NSMakeRect(left, 246, 120, 18)];
    self.historyPopup = [self popupWithItems:@[] frame:NSMakeRect(left, 212, width - 48 - 150, 28)];
    self.openHistoryButton = [self buttonWithTitle:@"Open Selected" action:@selector(openSelectedHistory:) frame:NSMakeRect(width - 24 - 130, 212, 130, 28)];

    NSScrollView *logScrollView = [[NSScrollView alloc] initWithFrame:NSMakeRect(left, 72, width - 48, 124)];
    logScrollView.hasVerticalScroller = YES;
    logScrollView.borderType = NSNoBorder;
    logScrollView.drawsBackground = NO;

    self.logView = [[NSTextView alloc] initWithFrame:NSMakeRect(0, 0, logScrollView.frame.size.width, logScrollView.frame.size.height)];
    self.logView.editable = NO;
    self.logView.selectable = YES;
    self.logView.font = [NSFont monospacedSystemFontOfSize:12 weight:NSFontWeightRegular];
    self.logView.backgroundColor = [NSColor colorWithCalibratedRed:0.11 green:0.13 blue:0.12 alpha:1.0];
    self.logView.textColor = [NSColor colorWithCalibratedRed:0.90 green:0.94 blue:0.92 alpha:1.0];
    self.logView.textContainerInset = NSMakeSize(12, 12);
    logScrollView.documentView = self.logView;

    NSString *version = [[[NSBundle mainBundle] infoDictionary] objectForKey:@"CFBundleShortVersionString"] ?: @"0.0.0";
    self.versionLabel = [self labelWithString:[NSString stringWithFormat:@"Version %@", version]
                                         font:[NSFont monospacedSystemFontOfSize:11 weight:NSFontWeightRegular]
                                        color:[self bodyTextColor]
                                        frame:NSMakeRect(left, 30, 160, 16)];

    for (NSView *view in @[
        titleLabel, subtitleLabel, inputModePrompt, self.inputModePopup, self.inputPromptLabel, self.urlField, self.chooseFileButton, variantPrompt, self.variantPopup,
        timeoutPrompt, self.timeoutPopup, maxPrompt, self.maxUrlsField, includePrompt,
        self.includeField, excludePrompt, self.excludeField, self.onlyFailedButton,
        self.generateIndexButton, self.blockMediaButton, self.startButton, self.pauseButton, self.stopButton,
        self.openOutputButton, self.revealButton, self.statusLabel, self.detailLabel,
        self.progressLabel, self.outputLabel, historyLabel, self.historyPopup, self.openHistoryButton,
        logScrollView, self.versionLabel, self.quitButton
    ]) {
        [content addSubview:view];
    }

    [self updateInputModeUI];
    [self refreshHistoryControls];
    [self updateButtons];
    [self appendLog:@"Native launcher ready.\n"];
}

- (NSString *)trimmedValue:(NSString *)value {
    return [value stringByTrimmingCharactersInSet:[NSCharacterSet whitespaceAndNewlineCharacterSet]];
}

- (BOOL)canStartRun {
    return !(self.runTask != nil && self.runTask.isRunning);
}

- (BOOL)canStopRun {
    return self.runTask != nil && self.runTask.isRunning;
}

- (BOOL)canPauseRun {
    return self.runTask != nil && self.runTask.isRunning;
}

- (BOOL)canOpenOutput {
    return self.lastOutputURL != nil;
}

- (BOOL)canOpenSelectedHistory {
    if (self.recentRuns.count == 0) {
        return NO;
    }
    NSInteger index = self.historyPopup.indexOfSelectedItem;
    if (index < 0 || index >= (NSInteger)self.recentRuns.count) {
        return NO;
    }
    NSString *path = self.recentRuns[(NSUInteger)index][@"output_path"] ?: @"";
    return path.length > 0 && [[NSFileManager defaultManager] fileExistsAtPath:path];
}

- (NSURL *)projectRootURL {
    NSURL *candidate = [[NSBundle mainBundle].bundleURL URLByDeletingLastPathComponent];
    NSFileManager *fileManager = [NSFileManager defaultManager];

    while (candidate != nil) {
        NSURL *pythonURL = [candidate URLByAppendingPathComponent:@".venv/bin/python"];
        NSURL *scriptURL = [candidate URLByAppendingPathComponent:@"screenshot.py"];
        if ([fileManager isExecutableFileAtPath:pythonURL.path] &&
            [fileManager fileExistsAtPath:scriptURL.path]) {
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

- (NSURL *)screenshotScriptURL {
    return [[self projectRootURL] URLByAppendingPathComponent:@"screenshot.py"];
}

- (NSArray<NSString *> *)currentCommandArgumentsWithError:(NSString **)errorMessage {
    BOOL fileMode = [[self inputModeKey] isEqualToString:@"file"];
    NSString *inputValue = [self trimmedValue:self.urlField.stringValue ?: @""];
    if (inputValue.length == 0) {
        if (errorMessage != NULL) {
            *errorMessage = fileMode ? @"Choose a website list file first." : @"Enter a website or sitemap first.";
        }
        return nil;
    }
    if (fileMode && ![[NSFileManager defaultManager] fileExistsAtPath:inputValue]) {
        if (errorMessage != NULL) {
            *errorMessage = [NSString stringWithFormat:@"List file not found: %@", inputValue];
        }
        return nil;
    }

    NSString *maxURLs = [self trimmedValue:self.maxUrlsField.stringValue ?: @""];
    if (maxURLs.length > 0) {
        NSCharacterSet *nonDigits = [[NSCharacterSet decimalDigitCharacterSet] invertedSet];
        if ([maxURLs rangeOfCharacterFromSet:nonDigits].location != NSNotFound || maxURLs.integerValue < 1) {
            if (errorMessage != NULL) {
                *errorMessage = @"Max URLs must be a positive whole number.";
            }
            return nil;
        }
    }

    NSURL *scriptURL = [self screenshotScriptURL];
    NSMutableArray<NSString *> *arguments = [NSMutableArray arrayWithArray:@[
        @"-u",
        scriptURL.path,
        @"--variant",
        self.variantPopup.selectedItem.title.lowercaseString ?: @"basic",
        @"--timeout-profile",
        self.timeoutPopup.selectedItem.title.lowercaseString ?: @"normal",
        @"--no-open",
        @"--event-stream",
        @"jsonl",
    ]];
    if (fileMode) {
        [arguments addObjectsFromArray:@[@"--url-file", inputValue]];
    } else {
        [arguments addObjectsFromArray:@[@"--url", inputValue]];
    }

    if (self.onlyFailedButton.state == NSControlStateValueOn) {
        [arguments addObject:@"--only-failed"];
    }
    if (self.generateIndexButton.state == NSControlStateValueOn) {
        [arguments addObject:@"--generate-index"];
    }
    if (self.blockMediaButton.state == NSControlStateValueOn) {
        [arguments addObject:@"--block-third-party-media"];
    }

    NSString *includeFilters = [self trimmedValue:self.includeField.stringValue ?: @""];
    if (includeFilters.length > 0) {
        [arguments addObject:@"--include"];
        [arguments addObject:includeFilters];
    }
    NSString *excludeFilters = [self trimmedValue:self.excludeField.stringValue ?: @""];
    if (excludeFilters.length > 0) {
        [arguments addObject:@"--exclude"];
        [arguments addObject:excludeFilters];
    }
    if (maxURLs.length > 0) {
        [arguments addObject:@"--max-urls"];
        [arguments addObject:maxURLs];
    }

    return arguments;
}

- (void)setInputsEnabled:(BOOL)enabled {
    self.urlField.editable = enabled;
    self.includeField.editable = enabled;
    self.excludeField.editable = enabled;
    self.maxUrlsField.editable = enabled;
    self.inputModePopup.enabled = enabled;
    self.variantPopup.enabled = enabled;
    self.timeoutPopup.enabled = enabled;
    self.onlyFailedButton.enabled = enabled;
    self.generateIndexButton.enabled = enabled;
    self.blockMediaButton.enabled = enabled;
    self.chooseFileButton.enabled = enabled && [[self inputModeKey] isEqualToString:@"file"];
}

- (void)setPausedState:(BOOL)paused {
    self.paused = paused;
    if (paused) {
        [self setStatus:@"Paused" detail:@"Run paused by user."];
    } else if (self.runTask != nil && self.runTask.isRunning && !self.stopRequested) {
        [self setStatus:@"Running" detail:@"The screenshot engine is active."];
    }
    [self updateButtons];
}

- (void)rememberCurrentRunInHistory {
    NSString *status = self.stopRequested ? @"Stopped" : ([self.statusLabel.stringValue length] > 0 ? self.statusLabel.stringValue : @"Finished");
    NSString *summary = self.totalPages > 0
        ? [NSString stringWithFormat:@"%ld/%ld pages", (long)MAX(self.pagesCompleted, self.currentPageIndex > 0 ? self.currentPageIndex - 1 : 0), (long)self.totalPages]
        : (self.detailLabel.stringValue ?: @"");
    NSString *outputPath = self.lastOutputURL.path ?: @"";
    NSDictionary *entry = @{
        @"label": self.currentRunLabel ?: @"Run",
        @"status": status,
        @"started_at": self.runStartedAt ?: @"",
        @"summary": summary ?: @"",
        @"output_path": outputPath,
    };
    [self.recentRuns insertObject:entry atIndex:0];
    while (self.recentRuns.count > 8) {
        [self.recentRuns removeLastObject];
    }
    [self saveHistory];
    [self refreshHistoryControls];
}

- (void)startRun:(id)sender {
    (void)sender;
    if (![self canStartRun]) {
        return;
    }

    NSURL *pythonURL = [self pythonURL];
    NSURL *scriptURL = [self screenshotScriptURL];
    if (![[NSFileManager defaultManager] isExecutableFileAtPath:pythonURL.path]) {
        [self setStatus:@"Missing Python"
                 detail:[NSString stringWithFormat:@"Expected virtual environment Python at %@", pythonURL.path]];
        [self appendLog:[NSString stringWithFormat:@"Missing Python executable: %@\n", pythonURL.path]];
        return;
    }
    if (![[NSFileManager defaultManager] fileExistsAtPath:scriptURL.path]) {
        [self setStatus:@"Missing screenshot.py"
                 detail:[NSString stringWithFormat:@"Expected screenshot.py at %@", scriptURL.path]];
        [self appendLog:[NSString stringWithFormat:@"Missing screenshot.py: %@\n", scriptURL.path]];
        return;
    }

    NSString *errorMessage = nil;
    NSArray<NSString *> *arguments = [self currentCommandArgumentsWithError:&errorMessage];
    if (arguments == nil) {
        [self setStatus:@"Input error" detail:errorMessage ?: @"Check the run options and try again."];
        return;
    }

    self.lastOutputURL = nil;
    self.stopRequested = NO;
    self.paused = NO;
    self.currentPageIndex = 0;
    self.totalPages = 0;
    self.pagesCompleted = 0;
    NSDateFormatter *formatter = [[NSDateFormatter alloc] init];
    formatter.dateFormat = @"yyyy-MM-dd HH:mm:ss";
    self.runStartedAt = [formatter stringFromDate:[NSDate date]];
    if ([[self inputModeKey] isEqualToString:@"file"]) {
        self.currentRunLabel = [self.urlField.stringValue lastPathComponent];
    } else {
        self.currentRunLabel = [self trimmedValue:self.urlField.stringValue ?: @""];
    }
    [self.lineBuffer setString:@""];
    self.logView.string = @"";
    [self setStatus:@"Starting"
             detail:@"Launching the native screenshot run..."];
    self.progressLabel.stringValue = @"Waiting for the screenshot engine to start...";
    self.outputLabel.stringValue = @"Last output: not available yet.";
    [self appendLog:[NSString stringWithFormat:@"Starting %@ %@\n", pythonURL.path, [arguments componentsJoinedByString:@" "]]];

    self.runTask = [[NSTask alloc] init];
    self.runTask.currentDirectoryURL = [self projectRootURL];
    self.runTask.executableURL = pythonURL;
    self.runTask.arguments = arguments;
    self.runTask.standardInput = [NSFileHandle fileHandleForReadingAtPath:@"/dev/null"];
    self.outputPipe = [NSPipe pipe];
    self.runTask.standardOutput = self.outputPipe;
    self.runTask.standardError = self.outputPipe;

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

    self.runTask.terminationHandler = ^(NSTask *task) {
        dispatch_async(dispatch_get_main_queue(), ^{
            [weakSelf runTaskDidTerminate:task];
        });
    };

    NSError *launchError = nil;
    if (![self.runTask launchAndReturnError:&launchError]) {
        [self setStatus:@"Failed to start"
                 detail:launchError.localizedDescription ?: @"Could not launch the screenshot engine."];
        [self appendLog:[NSString stringWithFormat:@"Launch failed: %@\n", launchError.localizedDescription ?: @"Unknown error"]];
        self.runTask = nil;
        self.outputPipe = nil;
        [self updateButtons];
        [self setInputsEnabled:YES];
        return;
    }

    [self setInputsEnabled:NO];
    [self updateButtons];
}

- (void)consumeOutput:(NSString *)text {
    [self.lineBuffer appendString:text];
    while (YES) {
        NSRange newlineRange = [self.lineBuffer rangeOfString:@"\n"];
        if (newlineRange.location == NSNotFound) {
            break;
        }
        NSString *line = [self.lineBuffer substringToIndex:newlineRange.location];
        [self.lineBuffer deleteCharactersInRange:NSMakeRange(0, newlineRange.location + newlineRange.length)];
        [self handleOutputLine:line];
    }
}

- (void)handleOutputLine:(NSString *)line {
    if (self.stopRequested) {
        NSArray<NSString *> *suppressedFragments = @[
            @"Future exception was never retrieved",
            @"TargetClosedError",
            @"Target page, context or browser has been closed",
            @"playwright._impl._errors.TargetClosedError",
        ];
        for (NSString *fragment in suppressedFragments) {
            if ([line containsString:fragment]) {
                return;
            }
        }
    }
    if ([line hasPrefix:kEventPrefix]) {
        NSString *jsonString = [line substringFromIndex:kEventPrefix.length];
        NSData *jsonData = [jsonString dataUsingEncoding:NSUTF8StringEncoding];
        if (jsonData != nil) {
            NSError *error = nil;
            NSDictionary *event = [NSJSONSerialization JSONObjectWithData:jsonData options:0 error:&error];
            if ([event isKindOfClass:[NSDictionary class]] && error == nil) {
                [self handleEvent:event];
                return;
            }
        }
    }
    [self appendLog:[line stringByAppendingString:@"\n"]];
}

- (void)handleEvent:(NSDictionary *)event {
    NSString *name = event[@"event"];
    if (![name isKindOfClass:[NSString class]]) {
        return;
    }

    if ([name isEqualToString:@"run_started"]) {
        [self setStatus:@"Running" detail:@"The screenshot engine is active."];
        return;
    }

    if ([name isEqualToString:@"site_started"]) {
        NSString *domain = event[@"domain"] ?: @"site";
        NSString *runFolder = event[@"run_folder"] ?: @"";
        if (![[self inputModeKey] isEqualToString:@"file"]) {
            self.currentRunLabel = domain;
        }
        self.progressLabel.stringValue = [NSString stringWithFormat:@"Preparing %@", domain];
        if ([runFolder isKindOfClass:[NSString class]] && runFolder.length > 0) {
            self.outputLabel.stringValue = [NSString stringWithFormat:@"Run folder: %@", runFolder];
        }
        return;
    }

    if ([name isEqualToString:@"site_urls_loaded"]) {
        NSNumber *totalURLs = event[@"total_urls"];
        NSString *source = event[@"source"] ?: @"sitemap";
        self.detailLabel.stringValue = [NSString stringWithFormat:@"Loaded %@ URLs from %@.", totalURLs ?: @0, source];
        return;
    }

    if ([name isEqualToString:@"site_urls_filtered"]) {
        NSNumber *totalURLs = event[@"total_urls"];
        self.detailLabel.stringValue = [NSString stringWithFormat:@"Ready to capture %@ pages.", totalURLs ?: @0];
        return;
    }

    if ([name isEqualToString:@"large_run_warning"]) {
        NSNumber *totalURLs = event[@"total_urls"];
        self.detailLabel.stringValue = [NSString stringWithFormat:@"Large run detected (%@ URLs). Continuing in app mode.", totalURLs ?: @0];
        return;
    }

    if ([name isEqualToString:@"page_started"]) {
        NSNumber *pageIndex = event[@"page_index"];
        NSNumber *totalPages = event[@"total_pages"];
        NSString *url = event[@"url"] ?: @"";
        self.currentPageIndex = pageIndex.integerValue;
        self.totalPages = totalPages.integerValue;
        self.progressLabel.stringValue = [NSString stringWithFormat:@"Page %@ of %@: %@", pageIndex ?: @0, totalPages ?: @0, url];
        return;
    }

    if ([name isEqualToString:@"viewport_started"]) {
        NSNumber *viewportIndex = event[@"viewport_index"];
        NSNumber *totalViewports = event[@"total_viewports"];
        NSString *viewport = event[@"viewport"] ?: @"viewport";
        self.detailLabel.stringValue = [NSString stringWithFormat:@"Capturing %@ (%@/%@).", viewport, viewportIndex ?: @0, totalViewports ?: @0];
        return;
    }

    if ([name isEqualToString:@"viewport_saved"]) {
        NSString *path = event[@"screenshot_path"] ?: @"";
        self.detailLabel.stringValue = [NSString stringWithFormat:@"Saved %@", path];
        return;
    }

    if ([name isEqualToString:@"page_finished"]) {
        NSNumber *successful = event[@"successful_viewports"];
        NSNumber *failed = event[@"failed_viewports"];
        NSNumber *pageIndex = event[@"page_index"];
        self.pagesCompleted = MAX(self.pagesCompleted, pageIndex.integerValue);
        self.detailLabel.stringValue = [NSString stringWithFormat:@"Page done. Successful viewports: %@, failed: %@.", successful ?: @0, failed ?: @0];
        return;
    }

    if ([name isEqualToString:@"site_finished"]) {
        NSString *runFolder = event[@"run_folder"] ?: @"";
        NSString *indexHTML = event[@"index_html"] ?: @"";
        NSNumber *pagesProcessed = event[@"pages_processed"];
        self.statusLabel.stringValue = @"Finished";
        self.detailLabel.stringValue = [NSString stringWithFormat:@"Finished %@ pages for %@.", pagesProcessed ?: @0, event[@"domain"] ?: @"site"];
        self.progressLabel.stringValue = @"Run completed successfully.";
        if ([indexHTML isKindOfClass:[NSString class]] && indexHTML.length > 0) {
            self.lastOutputURL = [NSURL fileURLWithPath:indexHTML];
            self.outputLabel.stringValue = [NSString stringWithFormat:@"Last output: %@", indexHTML];
        } else if ([runFolder isKindOfClass:[NSString class]] && runFolder.length > 0) {
            self.lastOutputURL = [NSURL fileURLWithPath:runFolder];
            self.outputLabel.stringValue = [NSString stringWithFormat:@"Last output: %@", runFolder];
        }
        [self updateButtons];
        return;
    }

    if ([name isEqualToString:@"site_failed"]) {
        self.statusLabel.stringValue = @"Failed";
        self.detailLabel.stringValue = [NSString stringWithFormat:@"Could not complete %@.", event[@"domain"] ?: @"site"];
        return;
    }

    if ([name isEqualToString:@"site_skipped"]) {
        self.statusLabel.stringValue = @"Stopped";
        self.detailLabel.stringValue = @"Run was stopped before screenshots started.";
        self.progressLabel.stringValue = @"No screenshots were captured.";
        return;
    }

    if ([name isEqualToString:@"run_aborted"]) {
        self.statusLabel.stringValue = self.stopRequested ? @"Stopped" : @"Aborted";
        self.detailLabel.stringValue = self.stopRequested ? @"Run stopped by user." : @"Run aborted.";
        return;
    }

    if ([name isEqualToString:@"run_finished"] && !self.stopRequested) {
        if ([self.statusLabel.stringValue isEqualToString:@"Running"] ||
            [self.statusLabel.stringValue isEqualToString:@"Starting"]) {
            self.statusLabel.stringValue = @"Finished";
            self.detailLabel.stringValue = @"Screenshot run finished.";
            self.progressLabel.stringValue = @"All work complete.";
        }
    }
}

- (void)runTaskDidTerminate:(NSTask *)task {
    (void)task;
    self.outputPipe.fileHandleForReading.readabilityHandler = nil;

    if (self.lineBuffer.length > 0) {
        NSString *remaining = [self.lineBuffer copy];
        [self.lineBuffer setString:@""];
        [self handleOutputLine:remaining];
    }

    int status = self.runTask.terminationStatus;
    self.runTask = nil;
    self.outputPipe = nil;
    self.paused = NO;
    [self setInputsEnabled:YES];

    if (self.quitAfterShutdown) {
        [NSApp replyToApplicationShouldTerminate:YES];
        return;
    }

    if (self.stopRequested) {
        [self setStatus:@"Stopped" detail:@"Run stopped by user."];
        self.progressLabel.stringValue = @"You can start a new run whenever you are ready.";
    } else if (status != 0 && ![self.statusLabel.stringValue isEqualToString:@"Failed"]) {
        [self setStatus:@"Failed"
                 detail:[NSString stringWithFormat:@"The screenshot engine ended with status %d.", status]];
    }

    [self rememberCurrentRunInHistory];
    self.stopRequested = NO;
    [self updateButtons];
}

- (void)openLastOutput:(id)sender {
    (void)sender;
    if (![self canOpenOutput]) {
        return;
    }
    [[NSWorkspace sharedWorkspace] openURL:self.lastOutputURL];
}

- (void)revealProjectFolder:(id)sender {
    (void)sender;
    [[NSWorkspace sharedWorkspace] openURL:[self projectRootURL]];
}

- (void)quitApp:(id)sender {
    (void)sender;
    [NSApp terminate:nil];
}

- (void)stopRun:(id)sender {
    (void)sender;
    if (![self canStopRun]) {
        return;
    }
    self.stopRequested = YES;
    if (self.paused) {
        kill(self.runTask.processIdentifier, SIGCONT);
        self.paused = NO;
    }
    [self setStatus:@"Stopping" detail:@"Stopping the active screenshot run..."];
    self.progressLabel.stringValue = @"Waiting for the engine to shut down cleanly...";
    [self appendLog:@"Stopping screenshot run...\n"];
    [self.runTask interrupt];
    [self scheduleForceStop];
    [self updateButtons];
}

- (void)togglePauseRun:(id)sender {
    (void)sender;
    if (![self canPauseRun]) {
        return;
    }
    int signalToSend = self.paused ? SIGCONT : SIGSTOP;
    if (kill(self.runTask.processIdentifier, signalToSend) == 0) {
        [self setPausedState:!self.paused];
        self.progressLabel.stringValue = self.paused
            ? @"Run paused. Resume whenever you are ready."
            : @"Run resumed.";
        [self appendLog:self.paused ? @"Run paused by user.\n" : @"Run resumed.\n"];
    }
}

- (void)scheduleForceStop {
    pid_t pid = self.runTask.processIdentifier;
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(5.0 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
        if (self.runTask == nil || !self.runTask.isRunning) {
            return;
        }
        kill(pid, SIGTERM);
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(2.0 * NSEC_PER_SEC)), dispatch_get_main_queue(), ^{
            if (self.runTask == nil || !self.runTask.isRunning) {
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
    BOOL canStart = [self canStartRun];
    BOOL canPause = [self canPauseRun];
    BOOL canStop = [self canStopRun];
    BOOL canOpenOutput = [self canOpenOutput];
    BOOL canOpenHistory = [self canOpenSelectedHistory];
    BOOL canChooseFile = !self.chooseFileButton.hidden && [self canStartRun];

    self.startButton.title = canStart ? @"Start Run" : @"Running";
    self.pauseButton.title = self.paused ? @"Resume Run" : @"Pause Run";
    self.stopButton.title = @"Stop Run";
    self.openOutputButton.title = @"Open Last Output";
    self.chooseFileButton.title = @"Choose File";
    self.openHistoryButton.title = @"Open Selected";
    self.revealButton.title = @"Open Project Folder";
    self.quitButton.title = @"Quit App";

    [self applyStyleToButton:self.startButton role:@"primary" enabled:canStart];
    [self applyStyleToButton:self.pauseButton role:@"secondary" enabled:canPause];
    [self applyStyleToButton:self.stopButton role:@"danger" enabled:canStop];
    [self applyStyleToButton:self.openOutputButton role:@"secondary" enabled:canOpenOutput];
    [self applyStyleToButton:self.chooseFileButton role:@"secondary" enabled:canChooseFile];
    [self applyStyleToButton:self.openHistoryButton role:@"secondary" enabled:canOpenHistory];
    [self applyStyleToButton:self.revealButton role:@"secondary" enabled:YES];
    [self applyStyleToButton:self.quitButton role:@"secondary" enabled:YES];
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
    if (fullText.length > 16000) {
        NSString *trimmed = [fullText substringFromIndex:fullText.length - 16000];
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
