#include <gtest/gtest.h>

namespace{
    struct SquareRootTest : public ::testing::Test {};
}

double sq(const double a) {
    return a * a;
}

TEST_F(SquareRootTest, PositiveNos) {
    ASSERT_EQ(36, sq(6.0));
    ASSERT_EQ(324.0, sq(18.0));
    ASSERT_EQ(645.16, sq(25.4));
    ASSERT_EQ(0, sq(0.0));
}

TEST_F(SquareRootTest, NegativeNos) {
    ASSERT_EQ(4.0, sq(-2.0));
    ASSERT_EQ(1.0, sq(-1.0));
}

int main(int argc, char **argv) {
    testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}