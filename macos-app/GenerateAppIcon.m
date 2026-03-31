#import <Cocoa/Cocoa.h>

static NSColor *Color(CGFloat r, CGFloat g, CGFloat b, CGFloat a) {
    return [NSColor colorWithCalibratedRed:r green:g blue:b alpha:a];
}

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc < 2) {
            fprintf(stderr, "Usage: GenerateAppIcon <output-png>\n");
            return 1;
        }

        NSString *outputPath = [NSString stringWithUTF8String:argv[1]];
        NSSize size = NSMakeSize(1024, 1024);
        NSImage *image = [[NSImage alloc] initWithSize:size];

        [image lockFocus];

        NSRect canvas = NSMakeRect(0, 0, size.width, size.height);
        [[NSColor clearColor] setFill];
        NSRectFill(canvas);

        NSShadow *shadow = [[NSShadow alloc] init];
        shadow.shadowColor = [Color(0.08, 0.15, 0.13, 0.24) colorWithAlphaComponent:0.24];
        shadow.shadowBlurRadius = 38.0;
        shadow.shadowOffset = NSMakeSize(0, -10);
        [NSGraphicsContext saveGraphicsState];
        [shadow set];

        NSBezierPath *outer = [NSBezierPath bezierPathWithRoundedRect:NSInsetRect(canvas, 54, 54) xRadius:230 yRadius:230];
        [[NSColor whiteColor] setFill];
        [outer fill];

        [NSGraphicsContext restoreGraphicsState];

        NSBezierPath *inner = [NSBezierPath bezierPathWithRoundedRect:NSInsetRect(canvas, 94, 94) xRadius:180 yRadius:180];
        NSGradient *background = [[NSGradient alloc] initWithColorsAndLocations:
                                  Color(0.95, 0.98, 0.96, 1.0), 0.0,
                                  Color(0.86, 0.93, 0.90, 1.0), 0.55,
                                  Color(0.80, 0.89, 0.86, 1.0), 1.0,
                                  nil];
        [background drawInBezierPath:inner angle:270];

        NSBezierPath *highlight = [NSBezierPath bezierPathWithOvalInRect:NSMakeRect(180, 640, 520, 280)];
        [[Color(1.0, 1.0, 1.0, 0.35) colorWithAlphaComponent:0.35] setFill];
        [highlight fill];

        NSBezierPath *window = [NSBezierPath bezierPathWithRoundedRect:NSMakeRect(210, 255, 604, 430) xRadius:70 yRadius:70];
        [[Color(0.15, 0.20, 0.18, 1.0) colorWithAlphaComponent:0.98] setFill];
        [window fill];

        NSBezierPath *topBar = [NSBezierPath bezierPathWithRoundedRect:NSMakeRect(210, 575, 604, 110) xRadius:70 yRadius:70];
        [[Color(0.19, 0.28, 0.25, 1.0) colorWithAlphaComponent:1.0] setFill];
        [topBar fill];

        NSRect topBarFlatRect = NSMakeRect(210, 575, 604, 55);
        [[Color(0.19, 0.28, 0.25, 1.0) colorWithAlphaComponent:1.0] setFill];
        NSRectFill(topBarFlatRect);

        NSArray<NSColor *> *dots = @[Color(0.99, 0.38, 0.34, 1.0), Color(0.97, 0.78, 0.29, 1.0), Color(0.31, 0.82, 0.43, 1.0)];
        CGFloat dotX = 270;
        for (NSColor *color in dots) {
            NSBezierPath *dot = [NSBezierPath bezierPathWithOvalInRect:NSMakeRect(dotX, 614, 30, 30)];
            [color setFill];
            [dot fill];
            dotX += 46;
        }

        NSBezierPath *content = [NSBezierPath bezierPathWithRoundedRect:NSMakeRect(260, 305, 504, 235) xRadius:42 yRadius:42];
        [[Color(0.96, 0.98, 0.97, 1.0) colorWithAlphaComponent:1.0] setFill];
        [content fill];

        NSBezierPath *stackBack = [NSBezierPath bezierPathWithRoundedRect:NSMakeRect(330, 360, 290, 185) xRadius:28 yRadius:28];
        [[Color(0.58, 0.77, 0.71, 1.0) colorWithAlphaComponent:0.35] setStroke];
        [stackBack setLineWidth:16.0];
        [stackBack stroke];

        NSBezierPath *stackFront = [NSBezierPath bezierPathWithRoundedRect:NSMakeRect(385, 330, 290, 185) xRadius:28 yRadius:28];
        [[Color(0.17, 0.45, 0.36, 1.0) colorWithAlphaComponent:0.95] setStroke];
        [stackFront setLineWidth:18.0];
        [stackFront stroke];

        NSBezierPath *frameTop = [NSBezierPath bezierPath];
        [frameTop moveToPoint:NSMakePoint(428, 486)];
        [frameTop lineToPoint:NSMakePoint(510, 486)];
        [frameTop moveToPoint:NSMakePoint(428, 486)];
        [frameTop lineToPoint:NSMakePoint(428, 438)];
        [frameTop moveToPoint:NSMakePoint(632, 486)];
        [frameTop lineToPoint:NSMakePoint(550, 486)];
        [frameTop moveToPoint:NSMakePoint(632, 486)];
        [frameTop lineToPoint:NSMakePoint(632, 438)];
        [frameTop moveToPoint:NSMakePoint(428, 360)];
        [frameTop lineToPoint:NSMakePoint(510, 360)];
        [frameTop moveToPoint:NSMakePoint(428, 360)];
        [frameTop lineToPoint:NSMakePoint(428, 408)];
        [frameTop moveToPoint:NSMakePoint(632, 360)];
        [frameTop lineToPoint:NSMakePoint(550, 360)];
        [frameTop moveToPoint:NSMakePoint(632, 360)];
        [frameTop lineToPoint:NSMakePoint(632, 408)];
        [[Color(0.17, 0.45, 0.36, 1.0) colorWithAlphaComponent:1.0] setStroke];
        [frameTop setLineWidth:16.0];
        [frameTop setLineCapStyle:NSLineCapStyleRound];
        [frameTop stroke];

        NSBezierPath *sun = [NSBezierPath bezierPathWithOvalInRect:NSMakeRect(470, 410, 120, 120)];
        [[Color(0.97, 0.80, 0.37, 1.0) colorWithAlphaComponent:0.92] setFill];
        [sun fill];

        [image unlockFocus];

        NSBitmapImageRep *representation = [[NSBitmapImageRep alloc] initWithData:[image TIFFRepresentation]];
        NSData *pngData = [representation representationUsingType:NSBitmapImageFileTypePNG properties:@{}];
        return [pngData writeToFile:outputPath atomically:YES] ? 0 : 1;
    }
}
