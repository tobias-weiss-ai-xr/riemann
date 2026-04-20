my(mf=mfinit([23,2],1));
my(B=mfeigenbasis(mf));
printf("num forms: %d\n", #B);

my(T2=mfhecke(mf,2));
printf("T_2 = %s\n", T2);

my(c=mfcoefs(B[1],5));
printf("coeffs B[1]: %s\n", c);

my(e1=mfembed(B[1]));
printf("mfembed type: %s\n", type(e1));
printf("mfembed length: %d\n", #e1);
printf("mfembed: %s\n", e1);

if(type(e1) == "t_VEC",
  printf("e1[1] type: %s\n", type(e1[1]));
  printf("e1[1] length: %d\n", #e1[1]));
  for(j=1, min(10,#e1[1]),
    printf("  a_%d = %s\n", j, e1[1][j]));
);
quit;
