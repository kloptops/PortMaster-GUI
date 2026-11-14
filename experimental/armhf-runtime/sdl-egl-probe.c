#include <SDL.h>
#include <stdio.h>
#include <stdlib.h>

static const char *env_or_unset(const char *name)
{
    const char *value = getenv(name);
    return value != NULL ? value : "<unset>";
}

int main(void)
{
    printf("SDL EGL/GLES probe\n");
    printf("SDL_VIDEODRIVER=%s\n", env_or_unset("SDL_VIDEODRIVER"));
    printf("SDL_VIDEO_EGL_DRIVER=%s\n", env_or_unset("SDL_VIDEO_EGL_DRIVER"));
    printf("SDL_VIDEO_GL_DRIVER=%s\n", env_or_unset("SDL_VIDEO_GL_DRIVER"));
    printf("EGL_PLATFORM=%s\n", env_or_unset("EGL_PLATFORM"));
    printf("WAYLAND_DISPLAY=%s\n", env_or_unset("WAYLAND_DISPLAY"));
    printf("XDG_RUNTIME_DIR=%s\n", env_or_unset("XDG_RUNTIME_DIR"));

    if (SDL_Init(SDL_INIT_VIDEO) != 0) {
        fprintf(stderr, "SDL_Init(video) failed: %s\n", SDL_GetError());
        return 1;
    }

    printf("SDL video driver: %s\n", SDL_GetCurrentVideoDriver());

    if (SDL_GL_SetAttribute(SDL_GL_CONTEXT_PROFILE_MASK,
                            SDL_GL_CONTEXT_PROFILE_ES) != 0 ||
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2) != 0 ||
        SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 0) != 0) {
        fprintf(stderr, "SDL_GL_SetAttribute failed: %s\n", SDL_GetError());
        SDL_Quit();
        return 2;
    }

    SDL_Window *window = SDL_CreateWindow(
        "RetroDECK ARMHF EGL probe",
        SDL_WINDOWPOS_UNDEFINED, SDL_WINDOWPOS_UNDEFINED,
        640, 480, SDL_WINDOW_OPENGL);
    if (window == NULL) {
        fprintf(stderr, "SDL_CreateWindow(OpenGL) failed: %s\n", SDL_GetError());
        SDL_Quit();
        return 3;
    }

    SDL_GLContext context = SDL_GL_CreateContext(window);
    if (context == NULL) {
        fprintf(stderr, "SDL_GL_CreateContext failed: %s\n", SDL_GetError());
        SDL_DestroyWindow(window);
        SDL_Quit();
        return 4;
    }

    printf("SDL_GL_CreateContext succeeded\n");
    SDL_GL_SwapWindow(window);
    SDL_Delay(250);
    SDL_GL_DeleteContext(context);
    SDL_DestroyWindow(window);
    SDL_Quit();
    return 0;
}
