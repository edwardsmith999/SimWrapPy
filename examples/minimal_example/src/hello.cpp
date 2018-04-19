// A program in C++
#include<iostream>
#include <fstream>

int main()
{

    int a, b;
    std::ifstream infile("./input/inputfile");
    std::string varname;
    infile >> varname >> a;
    infile >> varname >> b;
	std::cout << "Hello World " << a << " " << b << std::endl;
	return 0;
}
