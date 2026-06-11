package com.busgps.android.ui.superadmin

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.busgps.android.databinding.ItemSchoolBinding
import com.busgps.android.model.School

class SchoolAdapter(private val schools: List<School>) :
    RecyclerView.Adapter<SchoolAdapter.VH>() {

    inner class VH(val binding: ItemSchoolBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        VH(ItemSchoolBinding.inflate(LayoutInflater.from(parent.context), parent, false))

    override fun getItemCount() = schools.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        val school = schools[position]
        holder.binding.apply {
            tvSchoolName.text = school.name
            tvSchoolId.text = "ID: ${school.id}"
        }
    }
}
