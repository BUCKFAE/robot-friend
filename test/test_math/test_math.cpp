#include <MathUtils.h>
#include <unity.h>

void setUp(void) {}
void tearDown(void) {}

void test_add_positive(void) {
    TEST_ASSERT_EQUAL(5, add(2, 3));
}

void test_add_negative(void) {
    TEST_ASSERT_EQUAL(-1, add(2, -3));
}

void test_add_zero(void) {
    TEST_ASSERT_EQUAL(7, add(7, 0));
}

int main(int, char**) {
    UNITY_BEGIN();
    RUN_TEST(test_add_positive);
    RUN_TEST(test_add_negative);
    RUN_TEST(test_add_zero);
    return UNITY_END();
}
