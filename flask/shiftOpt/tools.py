def is_overlapping(time1, time2, time_allowance=0):
    start1, end1 = time1
    start2, end2 = time2

    # Adjust time1 by the time allowance
    adjusted_start2 = start2 - time_allowance
    adjusted_end2 = end2 + time_allowance

    # Check if the time ranges overlap
    return max(start1, adjusted_start2) < min(end1, adjusted_end2)

def calculate_time(time_schedule,longest = False):
    total_time = 0
    longest_time = -1
    if longest == True:
        for i in time_schedule:
            start, end = i
            time = end -start
            longest_time = max(longest_time,time)
            total_time += time
        return total_time,longest_time
    else:
        if type(time_schedule[0]) == list:
            for i in time_schedule:
                start, end = i
                total_time += end - start
        elif type(time_schedule[0]) == int:
            total_time = time_schedule[1] - time_schedule[0]
        return total_time

def calculate_required(time_schedule,required):
    if len(time_schedule) != len(required):
        raise Exception('length of time_schedule and required are different')
    cnt = 0
    for i in range(len(time_schedule)):
        cnt += required[i]
    return cnt

def split_list(lst, lengths):
    result = []
    index = 0

    for length in lengths:
        if index + length <= len(lst):
            result.append(lst[index:index + length])
            index += length
        else:
            raise ValueError("The sum of lengths exceeds the length of the list.")

    return result

def is_all_true(list):
    flag = True
    for i in list:
        if i == False:
            flag = False
    return flag