#include <SDL.h>
#include <stdio.h>
#include <stdlib.h>

typedef const unsigned char *(*gl_get_string_fn)(unsigned int name);

static const char *env_or_unset(const char *name)
{
    const char *value = getenv(name);
    return value != NULL ? value : "<unset>";
}

static void print_gl_string(const char *label, unsigned int name)
{
    gl_get_string_fn get_string =
        (gl_get_string_fn)SDL_GL_GetProcAddress("glGetString");
    const unsigned char *value = get_string != NULL ? get_string(name) : NULL;
    printf("%s=%s\n", label, value != NULL ? (const char *)value : "<unavailable>");
}

int main(int argc, char **argv)
{
    SDL_version version;
    SDL_GetVersion(&version);
    printf("SDL AArch64 EGL/GLES probe\n");
    printf("executable=%s\n", argc > 0 ? argv[0] : "<unknown>");
    printf("SDL_version=%u.%u.%u\n", version.major, version.minor, version.patch);
    printf("SDL_VIDEODRIVER=%s\n", env_or_unset("SDL_VIDEODRIVER"));
    printf("SDL_VIDEO_EGL_DRIVER=%s\n", env_or_unset("SDL_VIDEO_EGL_DRIVER"));
    printf("SDL_VIDEO_GL_DRIVER=%s\n", env_or_unset("SDL_VIDEO_GL_DRIVER"));
    printf("SDL_VIDEO_FORCE_EGL=%s\n", env_or_unset("SDL_VIDEO_FORCE_EGL"));
    printf("SDL_VIDEO_X11_FORCE_EGL=%s\n", env_or_unset("SDL_VIDEO_X11_FORCE_EGL"));
    printf("EGL_PLATFORM=%s\n", env_or_unset("EGL_PLATFORM"));
    printf("DISPLAY=%s\n", env_or_unset("DISPLAY"));
    printf("WAYLAND_DISPLAY=%s\n", env_or_unset("WAYLAND_DISPLAY"));
    printf("XDG_RUNTIME_DIR=%s\n", env_or_unset("XDG_RUNTIME_DIR"));

    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        fprintf(stderr, "RESULT=SDL_INIT_FAILED error=%s\n", SDL_GetError());
        return 1;
    }
    printf("SDL_video_driver=%s\n", SDL_GetCurrentVideoDriver());

    if (SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,
                            SDL_GL_CONTEXT_PROFILE_ES) != 0 ||
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2) != 0 ||
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 0) != 0) {
        fprintf(stderr, "RESULT=GL_ATTRIBUTES_FAILED error=%s\n", SDL_GetError());
        SDL_Quit();
        return 2;
    }

    SDL_Window *window = SDL_CreateWindow(
        "RetroDECK AArch64 EGL probe", SDL_WINDOWPOS_UNDEFINED,
        SDL_WINDOWPOS_UNDEFINED, 640, 480, SDL_WINDOW_OPENGL);
    if (window == NULL) {
        fprintf(stderr, "RESULT=WINDOW_FAILED error=%s\n", SDL_GetError());
        SDL_Quit();
        return 3;
    }
    printf("SDL_window=created\n");

    SDL_GLContext context = SDL_GL_CreateContext(window);
    if (context == NULL) {
        fprintf(stderr, "RESULT=CONTEXT_FAILED error=%s\n", SDL_GetError());
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 4;
    }

    printf("SDL_GL_context=created\n");
    print_gl_string("GL_VENDOR", 0x1F00);
    print_gl_string("GL_RENDERER", 0x1F01);
    print_gl_string("GL_VERSION", 0x1F02);
    SDL_GL_SwapWindow(window);
    SDL_Delay(200);
    SDL_GL_DeleteContext(context);
    SDL_DestroyWindow(window);
    SDL_Quit();
    puts("RESULT=SUCCESS");
    return 0;
}
