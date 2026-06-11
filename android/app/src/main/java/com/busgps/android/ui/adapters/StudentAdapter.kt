package com.busgps.android.ui.adapters

import com.busgps.android.R
import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.busgps.android.databinding.ItemStudentBinding
import com.busgps.android.model.Student

class StudentAdapter(
    private val students: List<Student>,
    private val onDelete: (String) -> Unit,
    private val onAssignBus: (String) -> Unit,
    private val onSetLocation: (Student) -> Unit = {}
) : RecyclerView.Adapter<StudentAdapter.VH>() {

    inner class VH(val binding: ItemStudentBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int) =
        VH(ItemStudentBinding.inflate(LayoutInflater.from(parent.context), parent, false))

    override fun getItemCount() = students.size

    override fun onBindViewHolder(holder: VH, position: Int) {
        val s = students[position]
        holder.binding.apply {
            tvName.text = s.name
            tvCode.text = s.code ?: "—"
            val hasLocation = s.lat != null && s.lng != null
            tvAddress.text = when {
                !s.addressText.isNullOrBlank() -> s.addressText
                hasLocation -> root.context.getString(R.string.location_set)
                else -> root.context.getString(R.string.no_home_location)
            }
            btnLocation.setOnClickListener { onSetLocation(s) }
            btnDelete.setOnClickListener { onDelete(s.id) }
            btnAssignBus.setOnClickListener { onAssignBus(s.id) }
        }
    }
}
