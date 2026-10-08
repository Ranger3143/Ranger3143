import math
def binom_sf(k,n,p=0.5):
    return sum(math.comb(n,i)*p**i*(1-p)**(n-i) for i in range(k,n+1))
def wilson(k,n,z=1.959963984540054):
    p=k/n;d=1+z*z/n;c=p+z*z/(2*n);h=z*math.sqrt((p*(1-p)+z*z/(4*n))/n);return 100*(c-h)/d,100*(c+h)/d
print('H9: P(X>=52|n=100,p=0.5) = %.3f'%binom_sf(52,100))
print('H9 pooled seeds 104/200: Wilson [%.1f-%.1f], P(X>=104|n=200,p=.5)=%.3f'%(*wilson(104,200),binom_sf(104,200)))
print('H9 seen placements 39/60 = %.1f%% [%.1f-%.1f]; held-out 13/40 = %.1f%% [%.1f-%.1f]'%(100*39/60,*wilson(39,60),100*13/40,*wilson(13,40)))
print('H6 op12k b: 6/30 Wilson [%.1f-%.1f]'%wilson(6,30))
print('H5 op12k 0/30 Wilson [%.1f-%.1f]; 2B 1/30 [%.1f-%.1f]'%(*wilson(0,30),*wilson(1,30)))
print('H7 op12k 79/150 [%.1f-%.1f]; per framing 33.3%%..73.3%%; threshold 3/30'%wilson(79,150))
print('H8 sign tests: pressure vs plain 8 vs 2 ->', 2*sum(math.comb(10,i)*0.5**10 for i in range(0,3)),'; guess vs plain 4 vs 2 ->',min(1,2*sum(math.comb(6,i)*0.5**6 for i in range(0,3))))
print('H1 C08 accepted 520/520; field-value 0/4825 Wilson upper %.2f%%'%wilson(0,4825)[1])
