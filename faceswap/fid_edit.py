import sys
import matplotlib.pyplot as plt 
import threading
from matplotlib.animation import FuncAnimation

loss_a = []
loss_b = []
iterations = []
n=0
cnt = 0
with open('/home/foscar/capston/faceswap/loss_score2.txt', 'r') as file: 
    for text in file: 
        line = text.strip('\n')
        cnt+=1
        if  10113<=cnt<=40000:
            s = [i for i in line.split()]
            #print(float(s[2]), float(s[5]))
            loss_a.append(float(s[2]))
            loss_b.append(float(s[5]))
            iterations.append(n*20)
            n+=1
# print("loss_a : ",loss_a)
# print("loss_b : ",loss_b)
# print("iterations :", iterations)

plt.figure(figsize=(10,6))
plt.plot(iterations,loss_a,'r',label='Generator Loss')
plt.plot(iterations, loss_b,'b',label='Discriminator Loss')
plt.xlabel('Iterations')
plt.ylabel('Loss')
plt.title('Loss per Iterations')
plt.legend() 
plt.show()
