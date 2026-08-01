/* ============================================================================
 * THE HEADER — "the menu"
 *
 * This is the only file someone using your module needs to read. It says WHAT
 * exists, never HOW it works. Types and function declarations, nothing else.
 *
 * This module is deliberately not one of the six katas. It exists so you can
 * see the three-file shape in something that actually compiles.
 * ==========================================================================*/

/* Include guard. `#include` literally pastes this file's text into another
 * file. If two files both include this one, the compiler would see everything
 * below twice and error out. This says: if THING_H hasn't been defined yet,
 * define it and carry on; otherwise skip to #endif. Every header has one, and
 * the name is conventionally the filename in shouty case. */
#ifndef CLAMP_H
#define CLAMP_H

/* Angle brackets < > for system headers, quotes " " for your own files. */
#include <stdint.h>   /* int32_t */
#include <stdbool.h>  /* bool, true, false */

/* A DECLARATION: signature, then a semicolon. No body. It promises "a function
 * with this name and shape exists somewhere" so other files can call it. */
int32_t clamp(int32_t value, int32_t lo, int32_t hi);

/* Returns true when value was already inside the range. Note the two-part
 * pattern you will use constantly in C: when a function needs to return two
 * things, one comes back as the return value and the other is written through
 * a pointer the caller supplies. */
bool clamp_checked(int32_t value, int32_t lo, int32_t hi, int32_t *out);

#endif /* CLAMP_H */
