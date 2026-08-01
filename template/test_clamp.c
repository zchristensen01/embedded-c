/* ============================================================================
 * THE TEST — "the critic"
 *
 * This file holds main(), so this is the program that actually runs.
 * `make test` compiles every .c in this directory together, so this file and
 * clamp.c become one binary.
 *
 * There is no test framework. assert() is the whole toolkit: it does nothing
 * when the condition is true, and prints the file and line and kills the
 * program when it is false.
 * ==========================================================================*/

#include <assert.h>
#include <stdio.h>
#include "clamp.h"

/* One function per behaviour. When an assert fires you get a line number, but
 * a named function tells you what you MEANT it to do. */
static void test_value_inside_range_is_unchanged(void)
{
    assert(clamp(5, 0, 10) == 5);
}

static void test_value_outside_range_is_pulled_in(void)
{
    assert(clamp(-3, 0, 10) == 0);
    assert(clamp(99, 0, 10) == 10);
}

static void test_exact_boundaries(void)
{
    /* The edges are where bugs live. The middle of the range was never going
     * to fail; these two catch `>` written where `>=` was meant. */
    assert(clamp(0,  0, 10) == 0);
    assert(clamp(10, 0, 10) == 10);
}

static void test_out_pointer_and_return_value_agree(void)
{
    int32_t out = 0;

    assert(clamp_checked(5, 0, 10, &out) == true);   /* &out = "address of out" */
    assert(out == 5);

    assert(clamp_checked(99, 0, 10, &out) == false);
    assert(out == 10);
}

int main(void)
{
    test_value_inside_range_is_unchanged();
    test_value_outside_range_is_pulled_in();
    test_exact_boundaries();
    test_out_pointer_and_return_value_agree();

    /* A passing assert is silent, so without this line a successful run looks
     * exactly like a run that did nothing. */
    printf("all tests passed\n");
    return 0;
}
