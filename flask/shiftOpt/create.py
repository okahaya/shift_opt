from openjij import SASampler, SQASampler
from pyqubo import Array, Constraint
from tools import*
class AssignJobType:
    def __init__(self,member_dict,jobs,time_schedules,requireds,time_allowance):
        self.member_dict = member_dict
        self.member = list(member_dict.keys())
        self.cantwork = list(member_dict.values())
        self.jobs = jobs
        self.time_schedules = time_schedules
        self.requireds = requireds
        self.required_each_job = self.calculate_required_each_job()
        self.time_allowance = time_allowance

    def calculate_required_each_job(self):
        required_each_job = [0 for i in range(len(self.jobs))]
        for i in range(len(self.jobs)):
            required_each_job[i] = calculate_required(time_schedule=self.time_schedules[i],required=self.requireds[i])
        return required_each_job

    def how_overlapping(self):
        overlap = [[0 for i in range(len(self.member))] for j in range(len(self.jobs))]
        for i in range(len(self.jobs)):
            for j in range(len(self.time_schedules[i])):
                for k in range(len(self.member)):
                    for l in self.cantwork[k]:
                        if is_overlapping(self.time_schedules[i][j],l,time_allowance=self.time_allowance):
                            overlap[i][k] += 1
        return overlap

    def make_assign_qubo(self,overlap):
        q = Array.create(name ="q", shape=(len(self.member),len(self.jobs)), vartype='BINARY')

        onehot = 0
        for i in range(len(self.member)):
            temp = 0
            for j in range(len(self.jobs)):
                temp += q[i][j]
            onehot += Constraint((1 - temp)**2, f'onehot_{i}',condition=lambda x: x==0.0)
        
        total_required = sum(self.required_each_job)
        average = len(self.member)/total_required
        equalizer = 0
        for j in range(len(self.jobs)):
            temp = 0
            for i in range(len(self.member)):
                temp += q[i][j]
            equalizer += ((temp - (average*self.required_each_job[j])))**2

        

        overlaps = 0
        for j in range(len(self.jobs)):        
            for i in range(len(self.member)):
                temp += overlap[j][i]*q[i][j]
            overlaps += temp/len(self.time_schedules[j])

        Q = 10*onehot + 10*equalizer + 5*overlaps/(len(self.member)*len(self.jobs))
        model = Q.compile()
        qubo,offset = model.to_qubo()
        return qubo,model

    def solve_assign_qubo(self,qubo):
        sampler = SASampler()
        sampleset = sampler.sample_qubo(qubo,num_reads=100)
        return sampleset

    def response_to_assign(self,sampleset,model):
        decoded_sample = model.decode_sample(sampleset.first.sample, vartype="BINARY")
        if decoded_sample.constraints(only_broken = True):
            print(decoded_sample.constraints(only_broken = True))
            return []
        sh = [[] for j in range(len(self.jobs))]
        for j in range(len(self.jobs)):
            for i in range(len(self.member)):
                if decoded_sample.array('q', (i, j)) > 0.8:
                    sh[j].append(i)
        return sh

    def create_assign(self):
        overlap = self.how_overlapping()
        qubo,model=self.make_assign_qubo(overlap)
        sampleset = self.solve_assign_qubo(qubo)
        assign = self.response_to_assign(sampleset,model)
        if len(assign) == 0:
            return []
        assign_list = []
        for i in range(len(self.jobs)):
            temp = {}
            for j in assign[i]:
                temp[self.member[j]] = self.member_dict[self.member[j]]
            assign_list.append(temp)
        return assign_list

class MakeShift:
    def __init__(self, member_dict, time_schedule, required, time_allowance,jobname):
        """
        member(dict):{members name(str):when members cant work(list(list))(Expressed by minutes from 0:00)
                                ex) cant work while 1:00 to 2:00 -> [60,120]
        time_schedule(list(list)):when workers are required(Expressed by minutes from 0:00)
        required(list(list)):the number of people required for each time period
        """
        self.member_dict = member_dict
        self.member = list(member_dict.keys())
        self.cantwork = list(member_dict.values())
        self.time_schedule = time_schedule
        self.required = required
        self.time_allowance = time_allowance
        self.jobname = jobname

    def make_overlapping_constraint(self,q):
        overlapping = 0
        for j in range(len(self.time_schedule)):
            for i in range(len(self.member)):
                for k in self.cantwork[i]:
                    if is_overlapping(self.time_schedule[j],k,time_allowance=0):
                        overlapping += q[i][j]
        for j in range(len(self.time_schedule)):
            for k in range(j,len(self.time_schedule)):
                if j == k:
                    continue
                if is_overlapping(self.time_schedule[j],self.time_schedule[k],time_allowance=self.time_allowance):
                    overlapping += sum(q[i][j]*q[i][k] for i in range(len(self.member))) 
        return overlapping

    def make_shift_qubo(self):
        # total_required = calculate_required(time_schedule=self.time_schedule,required=self.required)

        q = Array.create(name ="q", shape=(len(self.member),len(self.time_schedule)), vartype='BINARY')

        N_hot = Constraint(sum((self.required[j] - sum(q[i][j] for i in range(len(self.member))))**2 for j in range(len(self.time_schedule))),'n-hot',condition=lambda x: x==0.0)

        total_time,longest_time = calculate_time(time_schedule=self.time_schedule,longest=True)
        equalizer = sum((total_time/len(self.member)-sum(calculate_time(time_schedule=self.time_schedule[j])*q[i][j] for j in range(len(self.time_schedule))))**2 for i in range(len(self.member)))
        
        overlap = self.make_overlapping_constraint(q)
        overlapping = 0
        if type(overlap) != int:
            overlapping = Constraint(overlap,'overlapping_constraint',condition=lambda x: x==0.0)

        Q = 5*N_hot + equalizer/(longest_time**2) + 5*overlapping
        model = Q.compile()
        qubo,offset = model.to_qubo()
        return qubo,model

    def solve_shift_qubo(self,qubo):
        sampler = SASampler()
        sampleset = sampler.sample_qubo(qubo,num_reads=100)
        return sampleset

    def response_to_shift(self,sampleset,model):
        decoded_sample = model.decode_sample(sampleset.first.sample, vartype="BINARY")
        if decoded_sample.constraints(only_broken = True):
            print(f'broken constraint in creating shift  {self.jobname}  : {decoded_sample.constraints(only_broken = True)}')
            return []
        sh = []
        for j in range(len(self.time_schedule)):
            for i in range(len(self.member)):
                if decoded_sample.array('q', (i, j)) > 0.9:
                    sh.append(self.member[i])
        return sh
    def create_shift(self):
        qubo,model=self.make_shift_qubo()
        sampleset = self.solve_shift_qubo(qubo)
        shift_list = self.response_to_shift(sampleset,model)
        if len(shift_list) == 0:
            return shift_list
        shift_list = split_list(shift_list,self.required)

        return shift_list
