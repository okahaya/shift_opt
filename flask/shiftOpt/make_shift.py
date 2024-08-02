from create import*
from tools import is_all_true
def create_shift(member_dict, jobs, time_schedules, requireds,time_allowance=5):
    if len(member_dict) == 0:
        return -1
    if len(jobs) == 0:
        return -1
    if len(member_dict) < len(jobs):
        return -1
    if len(jobs) != 1:        
        test2 = AssignJobType(member_dict,jobs,time_schedules,requireds,time_allowance)
        succeed_assignment = False
        failed_cnt = 0
        while succeed_assignment == False:
            member_dicts = test2.create_assign()
            if len(member_dicts) != 0:
                succeed_assignment = True
            else:
                failed_cnt += 1
                print(failed_cnt,"Assignment")
            if failed_cnt == 3:
                return -1
    else:
        member_dicts = [member_dict]
    print(len(member_dicts[0]))
    print(jobs[0])
    shift = [[] for i in range(len(jobs))]
    succeed_make_shift = [False for i in range(len(jobs))]
    failed_cnt = 0
    while is_all_true(succeed_make_shift) == False:
        for i in range(len(jobs)):
            if succeed_make_shift[i] == True:
                continue
            print(f"start making shift {jobs[i]}")
            shift[i] = MakeShift(member_dict=member_dicts[i],time_schedule=time_schedules[i],required=requireds[i],time_allowance=5,jobname=jobs[i]).create_shift()
            if shift[i] != []:
                succeed_make_shift[i] = True
                print(f"succeed making shift {jobs[i]}")
                continue
            print(f"failed making shift {jobs[i]}")
        failed_cnt += 1
        if failed_cnt == 5:
            return -1
            
    return shift