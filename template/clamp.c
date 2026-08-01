/* ============================================================================
 * THE IMPLEMENTATION — "the kitchen"
 *
 * How it works. Nobody using the module needs to read this file.
 * ==========================================================================*/

/* Include your own header first. This is not style — it makes the compiler
 * check that the declarations in the header actually match the definitions
 * here. Get the two out of sync and you find out immediately. */
#include "clamp.h"

/* A DEFINITION: the same signature as in the header, now with a body. */
int32_t clamp(int32_t value, int32_t lo, int32_t hi)
{
    if (value < lo) {
        return lo;
    }
    if (value > hi) {
        return hi;
    }
    return value;
}

bool clamp_checked(int32_t value, int32_t lo, int32_t hi, int32_t *out)
{
    /* `*out = x` means "write x into the variable whose address the caller
     * handed me". That is how the second return value gets back. */
    *out = clamp(value, lo, hi);

    return (*out == value);
}

/* A helper used only inside this file would be marked `static`, which means
 * "not visible outside this file" — C's version of private. There isn't one
 * here, but in a real module most of them are static. */
