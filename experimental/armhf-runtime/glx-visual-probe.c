#include <GL/glx.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <stdio.h>

int main(void)
{
    Display *display = XOpenDisplay(NULL);
    if (display == NULL) {
        puts("X_OPEN_DISPLAY=failed");
        return 1;
    }
    puts("X_OPEN_DISPLAY=ok");

    int opcode = 0, event = 0, error = 0;
    int present = XQueryExtension(display, "GLX", &opcode, &event, &error);
    printf("X_GLX_EXTENSION=%s opcode=%d event=%d error=%d\n",
           present ? "present" : "absent", opcode, event, error);

    int screen = DefaultScreen(display);
    XVisualInfo template = { .screen = screen };
    int count = 0;
    XVisualInfo *visuals = XGetVisualInfo(display, VisualScreenMask,
                                         &template, &count);
    printf("X_VISUAL_COUNT=%d\n", count);
    if (visuals != NULL)
        XFree(visuals);

    if (present) {
        int major = 0, minor = 0;
        if (glXQueryVersion(display, &major, &minor))
            printf("GLX_VERSION=%d.%d\n", major, minor);
        else
            puts("GLX_VERSION=query-failed");

        int attributes[] = {
            GLX_RGBA, GLX_DOUBLEBUFFER,
            GLX_DEPTH_SIZE, 0,
            GLX_STENCIL_SIZE, 0,
            None
        };
        XVisualInfo *visual = glXChooseVisual(display, screen, attributes);
        if (visual != NULL) {
            printf("GLX_COMPAT_VISUAL=found id=0x%lx depth=%d class=%d\n",
                   visual->visualid, visual->depth, visual->class);
            XFree(visual);
        } else {
            puts("GLX_COMPAT_VISUAL=none");
        }
    } else {
        puts("GLX_COMPAT_VISUAL=not-available-without-extension");
    }

    XCloseDisplay(display);
    return present ? 0 : 2;
}
