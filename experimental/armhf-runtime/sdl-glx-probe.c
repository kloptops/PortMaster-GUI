#include <SDL.h>
#include <SDL_opengl.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <GL/glx.h>
#include <stdio.h>
#include <stdlib.h>

static const char *env_value(const char *name)
{
    const char *value = getenv(name);
    return value != NULL ? value : "<unset>";
}

int main(void)
{
    setvbuf(stdout, NULL, _IONBF, 0);
    printf("SDL desktop OpenGL / GLX probe\n");
    printf("SDL_VIDEODRIVER=%s\n", env_value("SDL_VIDEODRIVER"));
    printf("SDL_VIDEO_GL_DRIVER=%s\n", env_value("SDL_VIDEO_GL_DRIVER"));
    printf("SDL_VIDEO_EGL_DRIVER=%s\n", env_value("SDL_VIDEO_EGL_DRIVER"));
    printf("LIBGL_FB=%s\n", env_value("LIBGL_FB"));

    Display *display = XOpenDisplay(NULL);
    if (display == NULL) {
        fprintf(stderr, "XOpenDisplay failed\n");
        return 1;
    }
    int glx_opcode = 0, glx_event = 0, glx_error = 0;
    int glx_present = XQueryExtension(display, "GLX", &glx_opcode,
                                      &glx_event, &glx_error);
    printf("X_GLX_EXTENSION=%s opcode=%d event=%d error=%d\n",
           glx_present ? "present" : "absent",
           glx_opcode, glx_event, glx_error);
    int screen = DefaultScreen(display);
    XVisualInfo visual_template = { .screen = screen };
    int x_visual_count = 0;
    XVisualInfo *x_visuals = XGetVisualInfo(display, VisualScreenMask,
                                            &visual_template, &x_visual_count);
    printf("X_VISUAL_COUNT=%d\n", x_visual_count);
    if (x_visuals != NULL)
        XFree(x_visuals);

    if (glx_present) {
        int glx_major = 0, glx_minor = 0;
        if (glXQueryVersion(display, &glx_major, &glx_minor))
            printf("GLX_VERSION=%d.%d\n", glx_major, glx_minor);
        else
            puts("GLX_VERSION=query-failed");

        int visual_attributes[] = {
            GLX_RGBA, GLX_DOUBLEBUFFER,
            GLX_DEPTH_SIZE, 0,
            GLX_STENCIL_SIZE, 0,
            None
        };
        XVisualInfo *glx_visual = glXChooseVisual(display, screen,
                                                  visual_attributes);
        if (glx_visual != NULL) {
            printf("GLX_COMPAT_VISUAL=found id=0x%lx depth=%d class=%d\n",
                   glx_visual->visualid, glx_visual->depth,
                   glx_visual->class);
            XFree(glx_visual);
        } else {
            puts("GLX_COMPAT_VISUAL=none");
        }
    }
    XCloseDisplay(display);

    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        fprintf(stderr, "SDL_Init(video) failed: %s\n", SDL_GetError());
        return 1;
    }
    printf("SDL video driver: %s\n", SDL_GetCurrentVideoDriver());

    // Match nox-decomp/src/win.c exactly: it requests a desktop GL 2.1
    // double-buffered fullscreen desktop window with no depth or stencil.
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1);
    SDL_GL_SetAttribute(SDL_GL_DOUBLEBUFFER, 1);
    SDL_GL_SetAttribute(SDL_GL_DEPTH_SIZE, 0);
    SDL_GL_SetAttribute(SDL_GL_STENCIL_SIZE, 0);

    SDL_Window *window = SDL_CreateWindow(
        "RetroDECK ARMHF GLX probe",
        SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED,
        1024, 768, SDL_WINDOW_OPENGL | SDL_WINDOW_FULLSCREEN_DESKTOP);
    if (window == NULL) {
        fprintf(stderr, "SDL_CreateWindow(OpenGL) failed: %s\n", SDL_GetError());
        SDL_Quit();
        return 2;
    }
    puts("SDL_CreateWindow succeeded");

    SDL_GLContext context = SDL_GL_CreateContext(window);
    if (context == NULL) {
        fprintf(stderr, "SDL_GL_CreateContext failed: %s\n", SDL_GetError());
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 3;
    }
    puts("SDL_GL_CreateContext succeeded");
    printf("GL_VENDOR=%s\n", glGetString(GL_VENDOR));
    printf("GL_RENDERER=%s\n", glGetString(GL_RENDERER));
    printf("GL_VERSION=%s\n", glGetString(GL_VERSION));
    SDL_GL_SwapWindow(window);
    SDL_Delay(500);

    SDL_GL_DeleteContext(context);
    SDL_DestroyWindow(window);
    SDL_Quit();
    puts("RESULT=SUCCESS");
    return 0;
}
